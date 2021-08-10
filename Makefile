# cloudsigma cli

config:
	ccs config

create:
	ccs create

uninstall:
	pip uninstall -y ccs

install:
	pip install --use-feature=in-tree-build --upgrade .

devinstall: uninstall
	$(shell [ -e pyproject.toml ] && mv pyproject.toml .pyproject.toml)
	pip install --use-feature=in-tree-build --upgrade -e .[test,docs]
	$(shell [ -e .pyproject.toml ] && mv .pyproject.toml pyproject.toml)

clean:
	rm -f ~/.cloudsigma.conf
	rm -rf .pytest_cache
	rm -rf ./build
	find . -type d -name __pycache__ | xargs -r rm -rf
	find . -type d -name \*.egg-info | xargs -r rm -rf
	find . -type f -name \*.pyc | xargs -r rm
	cd docs; make clean
	pkill sphinx-serve || true
	rm -f .sphinx-serve.log

.PHONY: docs
docs:
	pkill sphinx-serve || true
	cd docs; make html
	(cd docs; sphinx-serve&)>>.sphinx-serve.log


TESTS=$(wildcard tests/test_*.py)
test:
	pytest tests/test_*.py
