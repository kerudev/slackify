try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        sync_playwright,
    )
except ImportError as e:
    raise RuntimeError(
        "To use the --browser flag, please install the browser dependencies:\n"
        "- pip install slackfm[browser]\n"
        "\n"
        "You may be asked to install additional dependencies for Playwright.\n"
    ) from e

import urllib.request
from typing import Any, TypedDict

from slackfm import log
from slackfm.constants import CONFIG_PATH
from slackfm.log import info
from slackfm.utils import dispatch, read_previous

STORAGE = CONFIG_PATH / "storage.json"


class PlaywrightCache(TypedDict):
    playwright: Playwright
    browser: Browser
    context: BrowserContext
    page: Page


_cache: PlaywrightCache = {}


def _read_selectors():
    ...


def _cleanup_status():
    ...


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
    _cache["page"].close()
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


def _clear_status(page: Page):
    locator = page.locator(".p-ia_member_profile__status__clear")

    if locator.count() > 0:
        locator.click()


def get_presence():
    page = _get_page()

    locator = page.locator(".c-presence.is-inline")
    locator.wait_for(state="attached")
    page.wait_for_timeout(200)  # wait to status to load

    classes = locator.evaluate("el => Array.from(el.classList)")

    if "c-presence--active" in classes:
        return "active"

    return "away"


def set_photo(cover_url):
    page = _get_page()
    _open_edit_profile(page)

    with page.expect_file_chooser() as fc_info:
        page.click('[data-qa="edit-profile-upload-button"]')

    req = urllib.request.Request(cover_url)
    response: bytes = dispatch(req)

    file_chooser = fc_info.value
    file_chooser.set_files(
        [{"name": "cover.jpg", "mimeType": "image/jpeg", "buffer": response}]
    )

    # TODO move .ord-nw and .ord-se so the image isn't cropped

    page.click('[data-qa="edit_profile_upload_save_button"]')

    page.click('[aria-label="Save Changes"]')


def get_profile() -> dict[str, Any]:
    page = _get_page()

    locator_image = page.locator(".p-r_member_profile__avatar__img")
    image_512 = locator_image.evaluate("el => el.src")

    locator_status = page.locator(".p-ia_member_profile__status__wrapper")
    status_text = locator_status.evaluate("el => el.textContent")

    status_emoji = ""

    if status_text:
        locator_emoji = page.locator(".c-custom_status__emoji_in_member_profile > img")
        status_emoji = locator_emoji.evaluate("el => el.dataset.stringifyEmoji")

    _clear_status(page)

    return {
        "status_expiration": 0,  # can't get this in the frontend
        "status_text": status_text,
        "status_emoji": status_emoji,
        "image_512": image_512,
    }


def set_profile(args):
    page = _get_page()
    _open_edit_status(page)

    button = page.locator('[data-qa="member_profile_status_btn"]')
    text = button.evaluate("el => el.textContent")

    log.info("Setting the song as the state")

    if text == "Set a status":
        emoji = args["status_emoji"].replace(":", "")

        page.click('[data-qa="custom_status_input_emoji_picker"]')
        page.fill('[data-qa="emoji_picker_input"]', emoji)
        page.click(f"#emoji-picker-{emoji}")

    menu = page.locator(".p-custom_status_modal")

    menu.locator(".ql-editor > p").fill(args["status_text"])
    menu.locator('[data-qa="custom_status_input_go"]').click()


def reset_profile():
    previous = read_previous()
    profile_picture = previous.pop("image_512")

    log.info("Resetting the profile info")
    set_profile(previous)

    log.info("Resetting the profile picture")
    set_photo(profile_picture)

    # TODO cleanup states created in runtime

    _stop_page()
