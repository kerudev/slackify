try:
    from playwright.sync_api import Page, Playwright, sync_playwright
except ImportError as e:
    raise RuntimeError(
        "To use the --browser flag, please install the browser dependencies:\n"
        "- pip install slackfm[browser]\n"
        "\n"
        "You may be asked to install additional dependencies for Playwright.\n"
    ) from e

from slackfm import log
from slackfm.api.slack import _get
from slackfm.constants import CONFIG_PATH
from slackfm.log import info

STORAGE = CONFIG_PATH / "storage.json"

_cache = {}


def _start_page():
    p = sync_playwright().start()

    if not STORAGE.exists():
        _fill_login_headful(p)

    browser = p.firefox.launch(headless=False)
    context = browser.new_context(storage_state=STORAGE)

    page = context.new_page()
    page.goto("https://app.slack.com/client/T08UMJSTMGV", wait_until="domcontentloaded")

    _open_user_menu(page)

    _cache["playwright"] = p
    _cache["browser"] = browser
    _cache["context"] = context
    _cache["page"] = page


def _stop_page():
    _cache["context"].close()
    _cache["browser"].close()
    _cache["playwright"].stop()


def _get_page() -> Page:
    if not _cache.get("page", None):
        _start_page()

    return _cache["page"]


def _fill_login_headful(p: Playwright):
    browser = p.firefox.launch(headless=False)
    context = browser.new_context()

    page = context.new_page()
    page.goto("https://app.slack.com/workspace-signin")

    input("Press enter when login is complete")

    context.storage_state(path=STORAGE)
    browser.close()

    info("==============================")
    info("              OK              ")
    info("==============================")


def _open_user_menu(page: Page):
    # Check if form is visible
    if page.is_visible('[aria-label="Edit Profile Form"]'):
        return

    if not page.is_visible(".p-view_contents"):
        log.info("Click on user profile to get menu")
        page.click(".p-ia__nav__user__button")

        log.info("Click the Profile option")
        page.click('.c-menu_item__label:text("Profile")')


def _open_edit_profile(page: Page):
    _open_user_menu(page)

    log.info("Click 'Edit' to change profile")
    page.click(".p-r_member_profile__name__edit")


def _open_edit_status(page: Page):
    _open_user_menu(page)

    log.info("Click 'Edit' to change status")
    page.click('[data-qa="member_profile_status_btn"]')


def get_presence():
    page = _get_page()
    _open_edit_profile(page)

    locator = page.locator(".c-presence.is-inline")
    classes = locator.evaluate("el => Array.from(el.classList)")

    if "c-presence--away" in classes:
        return "away"

    if "c-presence--active" in classes:
        return "active"

    return "unknown"


def set_photo(cover_url):
    response: bytes = _get(cover_url, parse_url=False)

    page = _get_page()
    _open_edit_profile(page)

    with page.expect_file_chooser() as fc_info:
        page.click('[data-qa="edit-profile-upload-button"]')

    file_chooser = fc_info.value
    file_chooser.set_files(
        [{"name": "cover.jpg", "mimeType": "image/jpeg", "buffer": response}]
    )

    page.click('[data-qa="edit_profile_upload_save_button"]')


def get_profile():
    page = _get_page()
    _open_edit_profile(page)

    locator = page.locator(".p-edit_profile__photo")
    image = locator.evaluate("el => el.src")

    return {"image_512": image}


def set_profile(args):
    pass


def reset_profile(previous_photo):
    _stop_page()

    return {}
