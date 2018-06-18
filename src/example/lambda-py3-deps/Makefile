SHELL := bash
TARGET := dist

# Runtime: Python 3.6
PIP := pip3
SOURCES := $(wildcard *.py)

.PHONY: all
all:
	@ rm -rf $(TARGET) && mkdir -p $(TARGET)
	@ printf '[install]\nprefix=\n' > setup.cfg # OSX hack

	$(PIP) install -U -t $(TARGET) -r requirements.txt | grep -i 'installed'
	/bin/cp -f $(SOURCES) $(TARGET)/

	@ rm -rf setup.cfg $(TARGET)/*.so $(TARGET)/*.dist-info
	@ find $(TARGET) -type f -name "*.py[cod]" -delete
	@ find $(TARGET) -type d -name "__pycache__" -print0 | xargs -0 rm -rf

	# Files for distribution:
	@ cd $(TARGET); find . -type f | sort -V | sed -e 's,^\./,  ,'
