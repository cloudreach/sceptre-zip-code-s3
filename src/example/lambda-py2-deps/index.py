import logging, sys
import ruamel.yaml as yaml
import helper

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def handler(event, context):
    logger.debug("Helper: %s" % helper.__welcome__)
    logger.debug("YAML: %s" % yaml.__version__)

    event.update({"helper": helper.__welcome__})

    result = yaml.safe_dump(event)
    logger.debug("Event in YAML:\n\n%s" % result)

    return result
