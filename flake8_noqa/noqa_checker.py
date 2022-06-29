"""Checker for noqa comments."""

from __future__ import annotations

import enum
import re
import tokenize
from typing import ClassVar, Iterator, Sequence, Tuple

import flake8_noqa

from typing_extensions import Protocol

from . import noqa_filter
from .noqa_comment import FileComment, InlineComment


try:
	try:
		from importlib.metadata import version
	except ModuleNotFoundError:  # python < 3.8 use polyfill
		from importlib_metadata import version  # type: ignore
	package_version = version(__package__)
except Exception:
	package_version = 'unknown'


SINGLE_SPACE = re.compile(r' [^\s]')


class Message(enum.Enum):
	"""Messages."""

	INLINE_NOQA_BAD_SPACE = (1, '"#{noqa}{sep}{codes}" must have a single space after the hash, e.g. "# {noqa_strip}{sep_codes_strip}"')
	INLINE_NOQA_NO_COLON = (2, '"#{noqa}{codes}" must have a colon, e.g. "# {noqa_strip}: {codes_strip}"')
	INLINE_NOQA_BAD_COLON_SPACE = (3, '"#{noqa}{sep}{codes}" must not have a space before the colon, e.g. "# {noqa_strip}: {codes_strip}"')
	INLINE_NOQA_BAD_CODE_SPACE = (4, '"#{noqa}{sep}{codes}" must have at most one space before the codes, e.g. "# {noqa_strip}: {codes_strip}"')
	INLINE_NOQA_DUPLICATE_CODE = (5, '"#{noqa}{sep}{codes}" has duplicate codes, remove {duplicates}')
	FILE_NOQA_BAD_SPACE = (11, '"#{flake8}{sep}{noqa}" must have a single space after the hash, e.g. "# {flake8_strip}{sep_colon}{noqa}"')
	FILE_NOQA_NO_COLON = (12, '"#{flake8}{noqa}" must have a colon or equals, e.g. "# {flake8_strip}:{noqa}"')
	FILE_NOQA_BAD_COLON_SPACE = (13, '"#{flake8}{sep}{noqa}" must not have a space before the {sep_name}, e.g. "# {flake8_strip}{sep_strip}{noqa}"')

	@property
	def code(self) -> str:
		"""Get code for message."""
		return (flake8_noqa.noqa_checker_prefix + str(self.value[0]).rjust(6 - len(flake8_noqa.noqa_checker_prefix), '0'))

	def text(self, **kwargs) -> str:
		"""Get formatted text of message."""
		return self.value[1].format(**kwargs)


class Options(Protocol):
	"""Protocol for options."""

	noqa_include_name: bool


class NoqaChecker:
	"""Check noqa comments for proper formatting."""

	name: ClassVar[str] = __package__.replace('_', '-')
	version: ClassVar[str] = package_version
	plugin_name: ClassVar[str]

	tokens: Sequence[tokenize.TokenInfo]
	filename: str

	@classmethod
	def parse_options(cls, options: Options) -> None:
		"""Parse plugin options."""
		cls.plugin_name = (' (' + cls.name + ')') if (options.noqa_include_name) else ''

	def __init__(self, logical_line: str, tokens: Sequence[tokenize.TokenInfo], filename: str) -> None:
		self.tokens = tokens
		self.filename = filename

	def _message(self, token: tokenize.TokenInfo, message: Message, **kwargs) -> Tuple[Tuple[int, int], str]:
		return (token.start, f'{message.code}{self.plugin_name} {message.text(**kwargs)}')

	def __iter__(self) -> Iterator[Tuple[Tuple[int, int], str]]:
		"""Primary call from flake8, yield error messages."""
		prev_token = None
		for token in self.tokens:
			if (tokenize.COMMENT != token.type):
				prev_token = token
				continue

			file_comment = FileComment.match(token)
			if (file_comment and (not file_comment.valid)):
				if (not SINGLE_SPACE.match(file_comment.flake8)):
					yield self._message(token, Message.FILE_NOQA_BAD_SPACE,
					                    flake8=file_comment.flake8, flake8_strip=file_comment.flake8.strip(),
					                    sep=file_comment.sep, sep_colon=(file_comment.sep or ':'),
					                    noqa=file_comment.noqa)
				if (not file_comment.sep):
					yield self._message(token, Message.FILE_NOQA_NO_COLON,
					                    flake8=file_comment.flake8, flake8_strip=file_comment.flake8.strip(),
					                    noqa=file_comment.noqa)
				else:
					if (not (file_comment.sep.startswith(':') or file_comment.sep.startswith('='))):
						yield self._message(token, Message.FILE_NOQA_BAD_COLON_SPACE,
						                    flake8=file_comment.flake8, flake8_strip=file_comment.flake8.strip(),
						                    sep=file_comment.sep, sep_strip=file_comment.sep.strip(),
						                    sep_name='colon' if (':' in file_comment.sep) else 'equals',
						                    noqa=file_comment.noqa)

			inline_comment = InlineComment.match(token, prev_token)
			if (inline_comment):
				noqa_filter.InlineComment.add_comment(self.filename, inline_comment)
				if (not inline_comment.valid):
					yield self._message(token, Message.INLINE_NOQA_BAD_SPACE,
					                    noqa=inline_comment.noqa, noqa_strip=inline_comment.noqa.strip(),
					                    sep=inline_comment.sep,
					                    codes=inline_comment.codes, sep_codes_strip=(f': {inline_comment.codes.strip()}' if (inline_comment.codes) else ''))

				if (inline_comment.codes):
					if (not inline_comment.sep):
						yield self._message(token, Message.INLINE_NOQA_NO_COLON,
						                    noqa=inline_comment.noqa, noqa_strip=inline_comment.noqa.strip(),
						                    sep=inline_comment.sep,
						                    codes=inline_comment.codes, codes_strip=inline_comment.codes.strip())
					else:
						if (not inline_comment.sep.startswith(':')):
							yield self._message(token, Message.INLINE_NOQA_BAD_COLON_SPACE,
							                    noqa=inline_comment.noqa, noqa_strip=inline_comment.noqa.strip(),
							                    sep=inline_comment.sep,
							                    codes=inline_comment.codes, codes_strip=inline_comment.codes.strip())

					if ((inline_comment.codes != inline_comment.codes.strip()) and not SINGLE_SPACE.match(inline_comment.codes)):
						yield self._message(token, Message.INLINE_NOQA_BAD_CODE_SPACE,
						                    noqa=inline_comment.noqa, noqa_strip=inline_comment.noqa.strip(),
						                    sep=inline_comment.sep,
						                    codes=inline_comment.codes, codes_strip=inline_comment.codes.strip())

					seen_codes = set()
					duplicates = []
					for code in inline_comment.code_list:
						if (code in seen_codes):
							duplicates.append(code)
						else:
							seen_codes.add(code)
					if (duplicates):
						yield self._message(token, Message.INLINE_NOQA_DUPLICATE_CODE,
						                    noqa=inline_comment.noqa, sep=inline_comment.sep, codes=inline_comment.codes,
						                    duplicates=', '.join(duplicates))
