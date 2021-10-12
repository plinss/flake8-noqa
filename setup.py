"""Define PyPI package."""

import flake8_noqa

import setuptools

with open("README.md", "r") as readme_file:
	long_description = readme_file.read()

setuptools.setup(
	name='flake8-noqa',
	version='1.999.999-dev',  # version will get replaced by git version tag - do not edit
	author='Peter Linss',
	author_email='pypi@linss.com',
	description='Flake8 noqa comment validation',
	long_description=long_description,
	long_description_content_type="text/markdown",
	url='https://github.com/plinss/flake8-noqa/',

	packages=['flake8_noqa'],
	package_data={'flake8_noqa': ['py.typed']},

	install_requires=[
		'flake8>=3.8.0,<5.0',
		'typing_extensions>=3.7.4.2,<4.0',
	],
	extras_require={
		'dev': [
			'mypy',
			'flake8<4.0',
			'flake8-annotations',
			'flake8-bugbear',
			'flake8-commas',
			'flake8-continuation',
			'flake8-datetimez',
			'flake8-docstrings',
			'flake8-import-order',
			'flake8-literal',
			'flake8-polyfill',
			'flake8-tabs',
			# 'flake8-smart-tabs',
			'flake8-type-annotations',
			'pep8-naming',
			'types-setuptools',
		],
		'test': [
			'flake8-docstrings',
		],
	},
	classifiers=[
		"Framework :: Flake8",
		"Environment :: Console",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
		"Programming Language :: Python",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
		"Programming Language :: Python :: 3.8",
		"Programming Language :: Python :: 3.9",
		"Programming Language :: Python :: 3.10",
		"Topic :: Software Development :: Libraries :: Python Modules",
		"Topic :: Software Development :: Quality Assurance",
	],
	python_requires='>=3.6',
	entry_points={
		'flake8.extension': [
			f'{flake8_noqa.noqa_checker_prefix} = flake8_noqa.noqa_checker:NoqaChecker',
			f'{flake8_noqa.noqa_filter_prefix} = flake8_noqa.noqa_filter:NoqaFilter',
		],
	},
)
