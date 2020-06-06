"""Filter for errors masked by noqa comments."""

import ast
import enum
import tokenize
from typing import Any, ClassVar, Dict, Iterator, List, Optional, Sequence, Set, Tuple

import flake8.checker
import flake8.defaults
import flake8.options.manager
import flake8.style_guide
import flake8.utils

import flake8_noqa

import pkg_resources

from typing_extensions import Protocol


try:
	package_version = pkg_resources.get_distribution(__package__).version
except pkg_resources.DistributionNotFound:
	package_version = 'unknown'


class Report:
	"""Violation report info."""

	reports: ClassVar[Dict[str, Dict[int, List[str]]]] = {}

	@classmethod
	def add_report(cls, filename: str, error_code: Optional[str], line_number: int, column: int, text: str) -> None:
		"""Add report to master list."""
		if (filename not in cls.reports):
			cls.reports[filename] = {}
		if (line_number not in cls.reports[filename]):
			cls.reports[filename][line_number] = []
		cls.reports[filename][line_number].append(error_code if (error_code is not None) else text.split(' ', 1)[0])

	@classmethod
	def reports_from(cls, filename: str, start_line: int, end_line: int) -> Sequence[str]:
		reports: List[str] = []
		for line_number in range(start_line, end_line + 1):
			reports += cls.reports.get(filename, {}).get(line_number, [])
		return reports


class NoqaComment:
	"""noqa comment info."""

	comments: ClassVar[Dict[str, List['NoqaComment']]] = {}

	codes: Set[str]
	start_line: int
	token: tokenize.TokenInfo

	@classmethod
	def add_comment(cls, filename: str, line_start_token: tokenize.TokenInfo, token: tokenize.TokenInfo, codes: Optional[str]) -> None:
		if (filename not in cls.comments):
			cls.comments[filename] = []
		cls.comments[filename].append(NoqaComment(line_start_token, token, codes))

	@classmethod
	def file_comments(cls, filename: str) -> Sequence['NoqaComment']:
		def start_line(comment: NoqaComment) -> int:
			return comment.start_line
		return sorted(cls.comments.get(filename, []), key=start_line)

	def __init__(self, line_start_token: tokenize.TokenInfo, token: tokenize.TokenInfo, codes: Optional[str]) -> None:
		self.codes = set(flake8.utils.parse_comma_separated_list(codes) if (codes) else [])
		self.start_line = line_start_token.start[0]
		self.token = token

	@property
	def end_line(self) -> int:
		return self.token.start[0]

	@property
	def text(self) -> str:
		match = flake8.defaults.NOQA_INLINE_REGEXP.match(self.token.string)
		return match.group(0) if (match) else '# noqa'

	def __repr__(self) -> str:
		return f'{self.start_line}-{self.end_line}:{self.codes}'


class Violation(flake8.style_guide.Violation):
    """Patch flake8 Violation class."""

    def is_inline_ignored(self, disable_noqa: bool) -> bool:
        """Always allow violations from this plugin."""
        if (self.code.startswith(flake8_noqa.plugin_prefix)):
        	return False
        return super().is_inline_ignored(disable_noqa)


class FileChecker(flake8.checker.FileChecker):
	"""Patch flake8 FileChecker class."""

	def run_ast_checks(self) -> None:
		"""Ensure this plugin is run last."""
		for index, plugin in enumerate(self.checks['ast_plugins']):
			if (flake8_noqa.noqa_filter_prefix == plugin['name']):
				self.checks['ast_plugins'].pop(index)
				self.checks['ast_plugins'].append(plugin)
				break
		super().run_ast_checks()

	def report(self, error_code: Optional[str], line_number: int, column: int, text: str) -> str:
		"""Capture report information."""
		Report.add_report(self.filename, error_code, line_number, column, text)
		return super().report(error_code, line_number, column, text)


class Message(enum.Enum):
	"""Messages."""

	NOQA_NO_VIOLATIONS = (1, 'No violations, remove "{comment}"')
	NOQA_NO_MATCHING_CODES = (2, 'No matching violations, remove "{comment}"')
	NOQA_UNUSED_CODES = (3, 'Unused {plural} present in "{comment}", remove {unused}')

	@property
	def code(self) -> str:
		return (flake8_noqa.noqa_filter_prefix + str(self.value[0]).rjust(6 - len(flake8_noqa.noqa_filter_prefix), '0'))

	def text(self, **kwargs) -> str:
		return self.value[1].format(**kwargs)


class Options(Protocol):
	"""Protocol for options."""

	noqa_include_name: bool


class NoqaFilter:
	"""Check noqa comments for proper formatting."""

	name: ClassVar[str] = __package__.replace('_', '-')
	version: ClassVar[str] = package_version
	plugin_name: ClassVar[str]
	require_code: ClassVar[bool]

	tree: ast.AST
	filename: str

	@classmethod
	def patch_flake8(cls) -> None:
		"""Replace flake8's FileChecker and Violation classes."""
		flake8.checker.FileChecker = FileChecker
		flake8.style_guide.Violation = Violation

	@classmethod
	def add_options(cls, option_manager: flake8.options.manager.OptionManager) -> None:
		cls.patch_flake8()

	@classmethod
	def parse_options(cls, options: Options) -> None:
		cls.plugin_name = (' (' + cls.name + ')') if (options.noqa_include_name) else ''

	def __init__(self, tree: ast.AST, filename: str) -> None:
		self.tree = tree
		self.filename = filename

	def _message(self, token: tokenize.TokenInfo, message: Message, **kwargs) -> Tuple[int, int, str, Any]:
		return (token.start[0], token.start[1], f'{message.code}{self.plugin_name} {message.text(**kwargs)}', type(self))

	def __iter__(self) -> Iterator[Tuple[int, int, str, Any]]:
		"""Primary call from flake8, yield error messages."""
		for comment in NoqaComment.file_comments(self.filename):
			reports = Report.reports_from(self.filename, comment.start_line, comment.end_line)
			if (comment.codes):
				used_codes: Set[str] = set()
				for code in reports:
					if (code in comment.codes):
						used_codes.add(code)
				if (used_codes):
					if (len(used_codes) < len(comment.codes)):
						unused_codes = comment.codes - used_codes
						yield self._message(comment.token, Message.NOQA_UNUSED_CODES,
						                    comment=comment.text, unused=', '.join(unused_codes),
						                    plural='codes' if (1 < len(unused_codes)) else 'code')
				else:
					yield self._message(comment.token, Message.NOQA_NO_MATCHING_CODES, comment=comment.text)

				pass
			elif (not reports):
				yield self._message(comment.token, Message.NOQA_NO_VIOLATIONS, comment=comment.text)
		pass
