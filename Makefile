
release-test:
	bumpversion patch
	python setup.py clean --all
	rm -rf dist
	python3 setup.py sdist
	twine upload --repository pypitest dist/*

release:
	bumpversion patch
	python setup.py clean --all
	rm -rf dist
	python3 setup.py sdist bdist_wheel
	twine upload dist/*