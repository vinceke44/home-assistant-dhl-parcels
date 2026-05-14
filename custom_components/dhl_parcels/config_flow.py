"""Config flow for DHL Parcels integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_CATEGORIES,
    DEFAULT_UPDATE_INTERVAL,
    CATEGORIES,
    ALL_CATEGORIES,
)
from . import DHLClient, DHLAuthError, DHLApiError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect to DHL."""
    client = DHLClient()

    def _try_login() -> None:
        client.login(data[CONF_EMAIL], data[CONF_PASSWORD])

    try:
        await hass.async_add_executor_job(_try_login)
    except DHLAuthError as err:
        raise InvalidAuth from err
    except DHLApiError as err:
        raise CannotConnect from err
    except Exception as err:  # noqa: BLE001
        raise CannotConnect from err

    return {"title": f"DHL Parcels ({data[CONF_EMAIL]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for DHL Parcels."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DHLParcelsOptionsFlowHandler:
        """Get the options flow for DHL Parcels."""
        return DHLParcelsOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step where the user enters credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=info["title"],
                    data=user_input,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception as err:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception during config flow: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle re-authentication with new credentials."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Unexpected exception during reauth: %s", err)
            errors["base"] = "unknown"
        else:
            existing_entry = await self.async_set_unique_id(
                user_input[CONF_EMAIL].lower()
            )
            if existing_entry:
                self.hass.config_entries.async_update_entry(
                    existing_entry, data=user_input
                )
                await self.hass.config_entries.async_reload(existing_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            _LOGGER.error("Reauth: could not find existing config entry to update")
            errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class DHLParcelsOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for DHL Parcels (interval settings and category filter)."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not user_input.get(CONF_CATEGORIES):
                errors[CONF_CATEGORIES] = "categories_empty"
            else:
                return self.async_create_entry(title="", data=user_input)

        current_categories = self.config_entry.options.get(
            CONF_CATEGORIES, list(CATEGORIES)
        )

        return self.async_show_form(
            step_id="init",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "update_interval",
                        default=self.config_entry.options.get(
                            "update_interval", DEFAULT_UPDATE_INTERVAL
                        ),
                    ): vol.All(int, vol.Range(min=60)),
                    vol.Required(
                        CONF_CATEGORIES,
                        default=current_categories,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(value=k, label=v)
                                for k, v in ALL_CATEGORIES.items()
                            ],
                            multiple=True,
                        )
                    ),
                }
            ),
        )
