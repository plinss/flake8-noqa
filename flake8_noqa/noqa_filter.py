"""Filter for errors masked by noqa comments."""

from __future__ import annotations

import enum
from typing import Any, ClassVar, Dict, Iterator, List, Optional, Sequence, Set, TYPE_CHECKING, Tuple

import flake8.checker
import flake8.defaults
import flake8.options.manager
import flake8.style_guide
import flake8.utils

import flake8_noqa

from typing_extensions import Protocol

from .noqa_comment import InlineComment

if (TYPE_CHECKING):
	import ast
	import tokenize


try:
	try:
		from importlib.metadata import version
	except ModuleNotFoundError:  # python < 3.8 use polyfill
		from importlib_metadata import version  # type: ignore
	package_version = version(__package__)
except Exception:
	package_version = 'unknown'


class Report:
	"""Violation report info."""

	reports: ClassVar[Dict[str, Dict[int, List[str]]]] = {}

	@classmethod
	def add_report(cls, filename: str, error_code: Optional[str], line_number: int, column: int, text: str) -> None:
		"""Add violation report to master list."""
		code = error_code if (error_code is not None) else text.split(' ', 1)[0]
		if (code.startswith(flake8_noqa.plugin_prefix)):
			return
		if (filename not in cls.reports):
			cls.reports[filename] = {}
		if (line_number not in cls.reports[filename]):
			cls.reports[filename][line_number] = []
		cls.reports[filename][line_number].append(code)

	@classmethod
	def reports_from(cls, filename: str, start_line: int, end_line: int) -> Sequence[str]:
		"""Get all volation reports for a range of lines."""
		reports: List[str] = []
		for line_number in range(start_line, end_line + 1):
			reports += cls.reports.get(filename, {}).get(line_number, [])
		return reports


class Message(enum.Enum):
	"""Messages."""

	NOQA_NO_VIOLATIONS = (1, '"{comment}" has no violations')
	NOQA_NO_MATCHING_CODES = (2, '"{comment}" has no matching violations')
	NOQA_UNMATCHED_CODES = (3, '"{comment}" has unmatched {plural}, remove {unmatched}')
	NOQA_REQUIRE_CODE = (4, '"{comment}" must have codes, e.g. "# {noqa_strip}: {codes}"')

	@property
	def code(self) -> str:
		"""Get code for message."""
		return (flake8_noqa.noqa_filter_prefix + str(self.value[0]).rjust(6 - len(flake8_noqa.noqa_filter_prefix), '0'))

	def text(self, **kwargs) -> str:
		"""Get formatted text of message."""
		return self.value[1].format(**kwargs)


class Options(Protocol):
	"""Protocol for options."""

	noqa_require_code: bool
	noqa_include_name: bool


class NoqaFilter:
	"""Check noqa comments for proper formatting."""

	name: ClassVar[str] = __package__.replace('_', '-')
	version: ClassVar[str] = package_version
	plugin_name: ClassVar[str]
	require_code: ClassVar[bool]
	_filters: ClassVar[List[NoqaFilter]] = []

	tree: ast.AST
	filename: str

	@classmethod
	def add_options(cls, option_manager: flake8.options.manager.OptionManager) -> None:
		"""Add plugin options to option manager."""
		option_manager.add_option('--noqa-require-code', default=False, action='store_true',
		                          parse_from_config=True, dest='noqa_require_code',
		                          help='Require code(s) to be included in  "# noqa:" comments (disabled by default)')
		option_manager.add_option('--noqa-no-require-code', default=False, action='store_false',
		                          parse_from_config=True, dest='noqa_require_code',
		                          help='Do not require code(s) in "# noqa" comments')
		option_manager.add_option('--noqa-include-name', default=False, action='store_true',
		                          parse_from_config=True, dest='noqa_include_name',
		                          help='Include plugin name in messages (enabled by default)')
		option_manager.add_option('--noqa-no-include-name', default=None, action='store_false',
		                          parse_from_config=False, dest='noqa_include_name',
		                          help='Remove plugin name from messages')

	@classmethod
	def parse_options(cls, options: Options) -> None:
		"""Parse plugin options."""
		cls.plugin_name = (' (' + cls.name + ')') if (options.noqa_include_name) else ''
		cls.require_code = options.noqa_require_code

	@classmethod
	def filters(cls) -> Sequence[NoqaFilter]:
		"""Get all filters."""
		return cls._filters

	@classmethod
	def clear_filters(cls) -> None:
		"""Clear filters."""
		cls._filters = []

	def __init__(self, tree: ast.AST, filename: str) -> None:
		self.tree = tree
		self.filename = filename
		self._filters.append(self)

	def __iter__(self) -> Iterator[Tuple[int, int, str, Any]]:
		"""Primary call from flake8, yield violations."""
		return iter([])

	def _message(self, token: tokenize.TokenInfo, message: Message, **kwargs) -> Tuple[int, int, str, Any]:
		return (token.start[0], token.start[1], f'{message.code}{self.plugin_name} {message.text(**kwargs)}', type(self))

	def violations(self) -> Iterator[Tuple[int, int, str, Any]]:
		"""Private iterator to return violations."""
		for comment in InlineComment.file_comments(self.filename):
			reports = Report.reports_from(self.filename, comment.start_line, comment.end_line)
			comment_codes = set(comment.code_list)
			if (comment_codes):
				matched_codes: Set[str] = set()
				for code in reports:
					if (code in comment_codes):
						matched_codes.add(code)
				if (matched_codes):
					if (len(matched_codes) < len(comment_codes)):
						unmatched_codes = comment_codes - matched_codes
						yield self._message(comment.token, Message.NOQA_UNMATCHED_CODES,
						                    comment=comment.text, unmatched=', '.join(unmatched_codes),
						                    plural='codes' if (1 < len(unmatched_codes)) else 'code')
				else:
					yield self._message(comment.token, Message.NOQA_NO_MATCHING_CODES, comment=comment.text)

				pass
			else:  # blanket noqa
				if (reports):
					if (self.require_code):
						yield self._message(comment.token, Message.NOQA_REQUIRE_CODE,
						                    comment=comment.text, noqa_strip=comment.noqa.strip(),
						                    codes=', '.join(sorted(reports)))

				else:
					yield self._message(comment.token, Message.NOQA_NO_VIOLATIONS, comment=comment.text)


class Violation(flake8.style_guide.Violation):
	"""Replacement for flake8's Violation class."""

	def is_inline_ignored(self, disable_noqa: bool, *args, **kwargs) -> bool:
		"""Prevent violations from this plugin from being ignored."""
		if (self.code.startswith(flake8_noqa.plugin_prefix)):
			return False
		return super().is_inline_ignored(disable_noqa, *args, **kwargs)


class FileChecker(flake8.checker.FileChecker):
	"""Replacement for flake8's FileChecker."""

	def run_checks(self, *args, **kwargs) -> Any:
		"""Get voilations from NoqaFilter after all other checks are run."""
		result = super().run_checks(*args, **kwargs)
		for filter in NoqaFilter.filters():
			for line_number, column, text, _ in filter.violations():
				self.report(error_code=None, line_number=line_number, column=column, text=text)
		NoqaFilter.clear_filters()
		return result

	def report(self, error_code: Optional[str], line_number: int, column: int, text: str, *args, **kwargs) -> str:
		"""Capture report information."""
		Report.add_report(self.filename, error_code, line_number, column, text)
		return super().report(error_code, line_number, column, text, *args, **kwargs)


# patch flake8
flake8.style_guide.Violation = Violation
flake8.checker.FileChecker = FileChecker
