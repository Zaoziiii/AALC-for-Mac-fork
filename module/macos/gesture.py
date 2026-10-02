"""Input release guarantee shared by dragging and linked attacks."""
from contextlib import contextmanager

@contextmanager
def held_mouse(driver, validate=lambda: None):
    validate()
    driver.mouseDown(_pause=False)
    try:
        yield
    finally:
        # PyAutoGUI's corner failsafe must not suppress a release.
        release(driver)

def release(driver):
    failsafe = driver.FAILSAFE
    try:
        driver.FAILSAFE = False
        driver.mouseUp(_pause=False)
    finally:
        driver.FAILSAFE = failsafe
