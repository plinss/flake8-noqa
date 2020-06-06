"""Checker for noqa comments."""

import enum
import re
import tokenize
from typing import ClassVar, Iterator, Sequence, Tuple

import flake8.defaults
import flake8.options.manager

import flake8_noqa

import pkg_resources

from typing_extensions import Protocol

from . import noqa_filter

try:
	package_version = pkg_resources.get_distribution(__package__).version
except pkg_resources.DistributionNotFound:
	package_version = 'unknown'


NOQA_FILE = re.compile(r'\s*#(?P<flake8>\s*flake8)(?P<sep>[:=])?(?P<noqa>(?:\b|\s*)noqa)', re.IGNORECASE)
NOQA_INLINE = re.compile(r'#(?P<noqa>\s*noqa)\b(?P<sep>:?)', re.IGNORECASE)
NOQA_INLINE_WITH_CODE = re.compile(r'#(?P<noqa>\s*noqa)\b(?P<sep>:?)(?P<codes>\s*([a-z]+[0-9]+(?:[,\s]+)?)+)', re.IGNORECASE)

SINGLE_SPACE = re.compile(r' [^\s]')


class Message(enum.Enum):
	"""Messages."""

	INLINE_NOQA_BAD_SPACE = (1, '"#{noqa}{sep}{codes}" must have a single space after the hash, e.g. "# {noqa_strip}{sep_codes_strip}"')
	INLINE_NOQA_NO_COLON = (2, '"#{noqa}{codes}" must have a colon, e.g. "# {noqa_strip}: {codes_strip}"')
	INLINE_NOQA_BAD_COLON_SPACE = (3, '"#{noqa}{sep}{codes}" must have at most one space before the codes, e.g. "# {noqa_strip}: {codes_strip}"')
	INLINE_NOQA_REQUIRE_CODE = (4, '"#{noqa}" comment must have one or more codes, e.g. "# {noqa_strip}: X000"')
	INLINE_NOQA_DUPLICATE_CODE = (5, '"#{noqa}{sep}{codes}" has duplicate codes, remove {duplicates}')
	FILE_NOQA_BAD_SPACE = (10, '"#{flake8}{sep}{noqa}" must have a single space after the hash, e.g. "# {flake8_strip}{sep_colon}{noqa}"')
	FILE_NOQA_NO_COLON = (11, '"#{flake8}{noqa}" must have a colon or equals, e.g. "# {flake8_strip}:{noqa}"')

	@property
	def code(self) -> str:
		return (flake8_noqa.noqa_filter_prefix + str(self.value[0]).rjust(6 - len(flake8_noqa.noqa_filter_prefix), '0'))

	def text(self, **kwargs) -> str:
		return self.value[1].format(**kwargs)


class Options(Protocol):
	"""Protocol for options."""

	noqa_require_code: bool
	noqa_include_name: bool


class NoqaChecker:
	"""Check noqa comments for proper formatting."""

	name: ClassVar[str] = __package__.replace('_', '-')
	version: ClassVar[str] = package_version
	plugin_name: ClassVar[str]
	require_code: ClassVar[bool]

	tokens: Sequence[tokenize.TokenInfo]
	filename: str

	@classmethod
	def add_options(cls, option_manager: flake8.options.manager.OptionManager) -> None:
		option_manager.add_option('--noqa-require-code', default=False, action='store_true',
		                          parse_from_config=True, dest='noqa_require_code',
		                          help='Require code(s) to be included in  "# noqa:" comments (disabled by default)')
		option_manager.add_option('--noqa-no-require-code', default=False, action='store_false',
		                          parse_from_config=True, dest='noqa_require_code',
		                          help='Do not require code(s) in "# noqa" comments')
		option_manager.add_option('--noqa-include-name', default=True, action='store_true',
		                          parse_from_config=True, dest='noqa_include_name',
		                          help='Include plugin name in messages (enabled by default)')
		option_manager.add_option('--noqa-no-include-name', default=None, action='store_false',
		                          parse_from_config=False, dest='noqa_include_name',
		                          help='Remove plugin name from messages')

	@classmethod
	def parse_options(cls, options: Options) -> None:
		cls.plugin_name = (' (' + cls.name + ')') if (options.noqa_include_name) else ''
		cls.require_code = options.noqa_require_code

	def __init__(self, logical_line: str, tokens: Sequence[tokenize.TokenInfo], filename: str) -> None:
		self.tokens = tokens
		self.filename = filename

	def _message(self, token: tokenize.TokenInfo, message: Message, **kwargs) -> Tuple[Tuple[int, int], str]:
		return (token.start, f'{message.code}{self.plugin_name} {message.text(**kwargs)}')

	def __iter__(self) -> Iterator[Tuple[Tuple[int, int], str]]:
		"""Primary call from flake8, yield error messages."""
		for token in self.tokens:
			if (tokenize.COMMENT != token.type):
				continue

			file_match = NOQA_FILE.match(token.string)
			if (file_match and (not flake8.defaults.NOQA_FILE.match(token.string))):
				flake8_str = file_match.group('flake8')
				sep = file_match.group('sep') or ''
				noqa = file_match.group('noqa')
				if (not SINGLE_SPACE.match(flake8_str)):
					yield self._message(token, Message.FILE_NOQA_BAD_SPACE,
					                    flake8=flake8_str, flake8_strip=flake8_str.strip(),
					                    sep=sep, sep_colon=sep or ':',
					                    noqa=noqa)
				if (not sep):
					yield self._message(token, Message.FILE_NOQA_NO_COLON,
					                    flake8=flake8_str, flake8_strip=flake8_str.strip(),
					                    noqa=file_match.group('noqa'))

			inline_match = NOQA_INLINE.match(token.string)
			if (inline_match):
				good_match = flake8.defaults.NOQA_INLINE_REGEXP.match(token.string)
				noqa = inline_match.group('noqa')
				sep = inline_match.group('sep') or ''
				code_match = NOQA_INLINE_WITH_CODE.match(token.string)
				codes = code_match.group('codes') if (code_match) else ''

				if (good_match):
					noqa_filter.NoqaComment.add_comment(self.filename, self.tokens[0], token, good_match.group('codes'))
				else:
					yield self._message(token, Message.INLINE_NOQA_BAD_SPACE,
					                    noqa=noqa, noqa_strip=noqa.strip(),
					                    sep=sep,
					                    codes=codes, sep_codes_strip=(f': {codes.strip()}' if (codes) else ''))

				if (code_match):
					if (not sep):
						yield self._message(token, Message.INLINE_NOQA_NO_COLON,
						                    noqa=noqa, noqa_strip=noqa.strip(),
						                    sep=sep,
						                    codes=codes, codes_strip=codes.strip())
					if ((codes != codes.strip()) and not SINGLE_SPACE.match(codes)):
						yield self._message(token, Message.INLINE_NOQA_BAD_COLON_SPACE,
						                    noqa=noqa, noqa_strip=noqa.strip(),
						                    sep=sep,
						                    codes=codes, codes_strip=codes.strip())

					seen_codes = set()
					duplicates = []
					for code in flake8.utils.parse_comma_separated_list(codes):
						if (code in seen_codes):
							duplicates.append(code)
						else:
							seen_codes.add(code)
					if (duplicates):
						yield self._message(token, Message.INLINE_NOQA_DUPLICATE_CODE,
						                    noqa=noqa, sep=sep, codes=codes,
						                    duplicates=', '.join(duplicates))
				elif (self.require_code):
					yield self._message(token, Message.INLINE_NOQA_REQUIRE_CODE,
					                    noqa=noqa, noqa_strip=noqa.strip())
