#!/usr/bin/env python3
"""Unit tests."""

import os
import subprocess
import tempfile
import unittest
from typing import List


def flake8(test: str, options: List[str] = None) -> List[str]:
	"""Run flake8 on test input and return output."""
	with tempfile.NamedTemporaryFile(delete=False) as temp_file:
		temp_file.write(test.encode('utf-8'))
	process = subprocess.Popen(['flake8', '--isolated', '--select=NQA', temp_file.name] + (options or []),
    	                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = process.communicate()
	os.remove(temp_file.name)
	if (stderr):
		return [f'0:0:{line}' for line in stderr.decode('utf-8').splitlines()]
	# print(repr(test), repr([line.split(':', 1)[1] for line in stdout.decode('utf-8').splitlines()]))
	return [(line.split(':', 1)[1] if (':' in line) else line) for line in stdout.decode('utf-8').splitlines()]


class TestFileScope(unittest.TestCase):
	"""Test file scope comments."""

	def test_valid(self) -> None:
		self.assertEqual(flake8('# flake8:noqa'), [])
		self.assertEqual(flake8('# flake8: noqa'), [])
		self.assertEqual(flake8('# flake8:  noqa'), [])
		self.assertEqual(flake8('# flake8=noqa'), [])
		self.assertEqual(flake8('# flake8= noqa'), [])
		self.assertEqual(flake8('# flake8=  noqa'), [])

	def test_no_colon(self) -> None:
		self.assertEqual(flake8('# FLAKE8 NOQA'), [
			'1:1: NQA012 "# FLAKE8 NOQA" must have a colon or equals, e.g. "# FLAKE8: NOQA"',
		])
		self.assertEqual(flake8('# FLAKE8  NOQA'), [
			'1:1: NQA012 "# FLAKE8  NOQA" must have a colon or equals, e.g. "# FLAKE8:  NOQA"',
		])

	def test_bad_colon(self) -> None:
		self.assertEqual(flake8('# FLAKE8 :NOQA'), [
			'1:1: NQA013 "# FLAKE8 :NOQA" must not have a space before the colon, e.g. "# FLAKE8:NOQA"',
		])
		self.assertEqual(flake8('# FLAKE8 : NOQA'), [
			'1:1: NQA013 "# FLAKE8 : NOQA" must not have a space before the colon, e.g. "# FLAKE8: NOQA"',
		])
		self.assertEqual(flake8('# FLAKE8 = NOQA'), [
			'1:1: NQA013 "# FLAKE8 = NOQA" must not have a space before the equals, e.g. "# FLAKE8= NOQA"',
		])

	def test_no_space(self) -> None:
		self.assertEqual(flake8('#flake8 noqa'), [
			'1:1: NQA011 "#flake8 noqa" must have a single space after the hash, e.g. "# flake8: noqa"',
			'1:1: NQA012 "#flake8 noqa" must have a colon or equals, e.g. "# flake8: noqa"',
		])


class TestInline(unittest.TestCase):
	"""Test inline comments."""

	maxDiff = None

	def test_notnoqa(self) -> None:
		self.assertEqual(flake8('# noqasar'), [])
		self.assertEqual(flake8('# unoqa'), [])

	def test_valid(self) -> None:
		self.assertEqual(flake8('x=1 # noqa'), [])
		self.assertEqual(flake8('x=1 # noqa:'), [])
		self.assertEqual(flake8('x=1 # noqa this is not a code'), [])
		self.assertEqual(flake8('x=1 # noqa - X101 is not a code'), [])

	def test_space(self) -> None:
		self.assertEqual(flake8('x=1 #NOQA'), [
			'1:5: NQA001 "#NOQA" must have a single space after the hash, e.g. "# NOQA"',
		])
		self.assertEqual(flake8('x=1 #  NOQA'), [
			'1:5: NQA001 "#  NOQA" must have a single space after the hash, e.g. "# NOQA"',
		])

	def test_valid_codes(self) -> None:
		self.assertEqual(flake8('x=1 # noqa:E225'), [])
		self.assertEqual(flake8('x=1 # noqa: E225'), [])
		self.assertEqual(flake8('x=1 # noqa: E225,'), [])
		self.assertEqual(flake8('x=1 # noqa: E225, E261'), [])
		self.assertEqual(flake8('x=1 # noqa: E225, E261,'), [])
		self.assertEqual(flake8('x=1 # noqa: E225,   ,  E261  ,  ,   '), [])

	def test_no_colon(self) -> None:
		self.assertEqual(flake8('x=1 # noqa E225'), [
			'1:5: NQA002 "# noqa E225" must have a colon, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 #noqa E225'), [
			'1:5: NQA001 "#noqa E225" must have a single space after the hash, e.g. "# noqa: E225"',
			'1:5: NQA002 "#noqa E225" must have a colon, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 # noqa  E225'), [
			'1:5: NQA002 "# noqa  E225" must have a colon, e.g. "# noqa: E225"',
			'1:5: NQA004 "# noqa  E225" must have at most one space before the codes, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 # noqa E225, E261'), [
			'1:5: NQA002 "# noqa E225, E261" must have a colon, e.g. "# noqa: E225, E261"',
		])

	def test_bad_colon(self) -> None:
		self.assertEqual(flake8('x=1 # noqa : E225'), [
			'1:5: NQA003 "# noqa : E225" must not have a space before the colon, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 #noqa : E225'), [
			'1:5: NQA001 "#noqa : E225" must have a single space after the hash, e.g. "# noqa: E225"',
			'1:5: NQA003 "#noqa : E225" must not have a space before the colon, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 # noqa  :  E225'), [
			'1:5: NQA003 "# noqa  :  E225" must not have a space before the colon, e.g. "# noqa: E225"',
			'1:5: NQA004 "# noqa  :  E225" must have at most one space before the codes, e.g. "# noqa: E225"',
		])
		self.assertEqual(flake8('x=1 # noqa : E225, E261'), [
			'1:5: NQA003 "# noqa : E225, E261" must not have a space before the colon, e.g. "# noqa: E225, E261"',
		])

	def test_codes(self) -> None:
		self.assertEqual(flake8('x=1 # noqa: X101'), [
			'1:5: NQA102 "# noqa: X101" has no matching violations',
		])
		self.assertEqual(flake8('x=1 # noqa: E225, X101'), [
			'1:5: NQA103 "# noqa: E225, X101" has unmatched code, remove X101',
		])
		self.assertEqual(flake8('x=1 # noqa: E225, E225'), [
			'1:5: NQA005 "# noqa: E225, E225" has duplicate codes, remove E225',
		])

	def test_multiline(self) -> None:
		self.assertEqual(flake8("x='''\n'''  # noqa: E225"), [])
		self.assertEqual(flake8("x='''\n''',  # noqa: E225"), [])

	def test_double(self) -> None:
		self.assertEqual(flake8('x=1 # type: ignore[type] # noqa: X101'), [
			'1:5: NQA102 "# noqa: X101" has no matching violations',
		])

	def test_require_code(self) -> None:
		self.assertEqual(flake8('x=1 # noqa', ['--noqa-require-code']), [
			'1:5: NQA104 "# noqa" must have codes, e.g. "# noqa: D100, E225, E261, W292"',
		])

	def test_inlude_name(self) -> None:
		self.assertEqual(flake8('x=1 # noqa E225', ['--noqa-include-name']), [
			'1:5: NQA002 (flake8-noqa) "# noqa E225" must have a colon, e.g. "# noqa: E225"',
		])


if __name__ == '__main__':
	unittest.main()
