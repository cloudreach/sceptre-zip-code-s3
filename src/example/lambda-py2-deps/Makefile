SHELL := bash
TARGET := dist

# Runtime: Python 2.7
PIP := pip2
SOURCES := $(wildcard *.py)

.PHONY: all
all:
	@ rm -rf $(TARGET) && mkdir -p $(TARGET)
	@ printf '[install]\nprefix=\n' > setup.cfg # OSX hack

	$(PIP) install -U -t $(TARGET) -r requirements.txt | grep -i 'installed'
	/bin/cp -f $(SOURCES) $(TARGET)/

	@ rm -rf setup.cfg $(TARGET)/*.so $(TARGET)/*.dist-info
	@ find $(TARGET) -type f -name "*.py[cod]" -delete

	# Files for distribution:
	@ cd $(TARGET); find . -type f | sort -V | sed -e 's,^\./,  ,'
