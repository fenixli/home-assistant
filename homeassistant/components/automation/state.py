"""
Offer state listening automation rules.

For more details about this automation rule, please refer to the documentation
at https://home-assistant.io/docs/automation/trigger/#state-trigger
"""
import asyncio
import voluptuous as vol

from homeassistant.core import callback
from homeassistant.const import MATCH_ALL, CONF_PLATFORM, CONF_FOR
from homeassistant.helpers.event import (
    async_track_state_change, async_track_same_state)
import homeassistant.helpers.config_validation as cv

CONF_ENTITY_ID = 'entity_id'
CONF_FROM = 'from'
CONF_TO = 'to'

TRIGGER_SCHEMA = vol.All(vol.Schema({
    vol.Required(CONF_PLATFORM): 'state',
    vol.Required(CONF_ENTITY_ID): cv.entity_ids,
    # These are str on purpose. Want to catch YAML conversions
    vol.Optional(CONF_FROM): str,
    vol.Optional(CONF_TO): str,
    vol.Optional(CONF_FOR): vol.All(cv.time_period, cv.positive_timedelta),
}), cv.key_dependency(CONF_FOR, CONF_TO))


@asyncio.coroutine
def async_trigger(hass, config, action):
    """Listen for state changes based on configuration."""
    entity_id = config.get(CONF_ENTITY_ID)
    from_state = config.get(CONF_FROM, MATCH_ALL)
    to_state = config.get(CONF_TO, MATCH_ALL)
    time_delta = config.get(CONF_FOR)
    match_all = (from_state == MATCH_ALL and to_state == MATCH_ALL)
    async_remove_track_same = None

    @callback
    def state_automation_listener(entity, from_s, to_s):
        """Listen for state changes and calls action."""
        nonlocal async_remove_track_same

        @callback
        def call_action():
            """Call action with right context."""
            hass.async_run_job(action, {
                'trigger': {
                    'platform': 'state',
                    'entity_id': entity,
                    'from_state': from_s,
                    'to_state': to_s,
                    'for': time_delta,
                }
            })

        # Ignore changes to state attributes if from/to is in use
        if (not match_all and from_s is not None and to_s is not None and
                from_s.last_changed == to_s.last_changed):
            return

        if not time_delta:
            call_action()
            return

        async_remove_track_same = async_track_same_state(
            hass, to_s.state, time_delta, call_action, entity_ids=entity_id)

    unsub = async_track_state_change(
        hass, entity_id, state_automation_listener, from_state, to_state)

    @callback
    def async_remove():
        """Remove state listeners async."""
        unsub()
        if async_remove_track_same:
            async_remove_track_same()  # pylint: disable=not-callable

    return async_remove
