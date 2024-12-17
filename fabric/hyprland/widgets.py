import gi
import re
import json
from loguru import logger
from fabric.core.service import Property
from collections.abc import Iterable, Callable
from typing import Literal
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.eventbox import EventBox
from fabric.hyprland.service import Hyprland, HyprlandEvent
from fabric.utils.helpers import FormattedString, bulk_connect, truncate

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


connection: Hyprland | None = None


def get_hyprland_connection() -> Hyprland:
    global connection
    if not connection:
        connection = Hyprland()

    return connection


class WorkspaceButton(Button):
    """A button intented to be used with the `Workspaces` widget

    It implements fields specific its usage (e.g. the `active`, `urgent` and `empty` properties)

    .. tip::

        For CSS styling, this button adds a style class for each state of its own
    """

    @Property(int, "readable")
    def id(self) -> int:
        return self._id

    @Property(bool, "read-write", default_value=False)
    def active(self) -> bool:
        """Whether this is the currently active workspace button or not

        The style class `active` should be set if this is the currently active button

        :rtype: bool
        """
        return self._active

    @active.setter
    def active(self, value: bool):
        self._active = value
        if value is True:
            self.urgent = False
        (self.remove_style_class if not value else self.add_style_class)("active")
        return self.do_bake_label()

    @Property(bool, "read-write", default_value=False)
    def urgent(self) -> bool:
        """Whether the workspace associated with this button is currently urgent or not

        The style class `urgent` should be set if the workspace was marked as urgent

        :rtype: bool
        """
        return self._urgent

    @urgent.setter
    def urgent(self, value: bool):
        self._urgent = value
        (self.remove_style_class if not value else self.add_style_class)("urgent")
        return self.do_bake_label()

    @Property(bool, "read-write", default_value=True)
    def empty(self) -> bool:
        """Whether the workspace associated with this button is marked as empty or not

        The style class `empty` should be set if the workspace was marked as empty

        :rtype: bool
        """
        return self._empty

    @empty.setter
    def empty(self, value: bool):
        self._empty = value
        (self.remove_style_class if not value else self.add_style_class)("empty")
        return self.do_bake_label()

    def __init__(
        self,
        id: int,
        label: FormattedString | str | None = None,
        image: Gtk.Image | None = None,
        child: Gtk.Widget | None = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        """
        :param id: the identifier of this button's workspace
        :type id: int
        :param label: lazily evaluated string to be used as the label of this button, the button itself is available via the formatter field `button`, defaults to None
        :type label: FormattedString | str | None, optional
        :param image: an image widget to be added inside this button, defaults to None
        :type image: Gtk.Image | None, optional
        :param child: a child widget to put inside this button, defaults to None
        :type child: Gtk.Widget | None, optional
        :param name: the name identifer for this widget (useful for styling), defaults to None
        :type name: str | None, optional
        :param visible: whether should this widget be visible or not once initialized, defaults to True
        :type visible: bool, optional
        :param all_visible: whether should this widget and all of its children be visible or not once initialized, defaults to False
        :type all_visible: bool, optional
        :param style: inline stylesheet to be applied on this widget, defaults to None
        :type style: str | None, optional
        :param style_classes: a list of style classes to be added into this widget once initialized, defaults to None
        :type style_classes: Iterable[str] | str | None, optional
        :param tooltip_text: the text that should be rendered inside the tooltip, defaults to None
        :type tooltip_text: str | None, optional
        :param tooltip_markup: same as `tooltip_text` but it accepts simple markup expressions, defaults to None
        :type tooltip_markup: str | None, optional
        :param h_align: horizontal alignment of this widget (compared to its parent), defaults to None
        :type h_align: Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None, optional
        :param v_align: vertical alignment of this widget (compared to its parent), defaults to None
        :type v_align: Literal["fill", "start", "end", "center", "baseline"] | Gtk.Align | None, optional
        :param h_expand: whether should this widget fill in all the available horizontal space or not, defaults to False
        :type h_expand: bool, optional
        :param v_expand: whether should this widget fill in all the available vertical space or not, defaults to False
        :type v_expand: bool, optional
        :param size: a fixed size for this widget (not guranteed to get applied), defaults to None
        :type size: Iterable[int] | int | None, optional
        """
        super().__init__(
            None,
            image,
            child,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )
        self._id: int = id
        self._label: FormattedString | None = (
            FormattedString(label) if isinstance(label, str) else label
        )
        self._active: bool = False
        self._urgent: bool = False
        self._empty: bool = True

        self.active = False
        self.urgent = False
        self.empty = True

    def do_bake_label(self):
        if not self._label:
            return
        return self.set_label(self._label.format(button=self))


class Workspaces(EventBox):
    """Implementation of a commonly used workspaces widget for Hyprland"""

    @staticmethod
    def default_buttons_factory(workspace_id: int):
        """
        The default workspace buttons factory

        The button it bakes uses the given workspace ID as its label
        """
        return WorkspaceButton(id=workspace_id, label=str(workspace_id))

    def __init__(
        self,
        buttons: Iterable[WorkspaceButton] | None = None,
        buttons_factory: Callable[[int], WorkspaceButton | None]
        | None = default_buttons_factory,
        invert_scroll: bool = False,
        empty_scroll: bool = False,
        **kwargs,
    ):
        """

        :param buttons: a list of predefined buttons, if a workspace was opened but no button representing it in the given list was found, call the buttons factory function to create a button for that workspace, defaults to None
        :type buttons: Iterable[WorkspaceButton] | None, optional
        :param buttons_factory: a factory for creating buttons once they're needed, the given function will only be called if no button was found for the new workspace in the given list of predefined buttons, the function can return None instead of a button to ignore adding that workspace, defaults to default_buttons_factory
        :type buttons_factory: Callable[[int], WorkspaceButton  |  None] | None, optional
        :param invert_scroll: invert the scroll wheel's direction (for switching via the wheel), defaults to False
        :type invert_scroll: bool, optional
        :param empty_scroll: scroll through empty workspaces (if found in the list), defaults to False
        :type empty_scroll: bool, optional
        """
        super().__init__(events="scroll")
        self.connection = get_hyprland_connection()
        self._container = Box(**kwargs)
        self.children = self._container

        self._active_workspace: int | None = None
        self._buttons: dict[int, WorkspaceButton] = {}
        self._buttons_preset: list[WorkspaceButton] = [
            button for button in buttons or ()
        ]
        self._buttons_factory = buttons_factory
        self._invert_scroll = invert_scroll
        self._empty_scroll = empty_scroll

        bulk_connect(
            self.connection,
            {
                "event::workspace": self.on_workspace,
                "event::createworkspace": self.on_createworkspace,
                "event::destroyworkspace": self.on_destroyworkspace,
                "event::urgent": self.on_urgent,
            },
        )

        # all aboard...
        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)
        self.connect("scroll-event", self.scroll_handler)

    def on_ready(self, _):
        open_workspaces: tuple[int, ...] = tuple(
            workspace["id"]
            for workspace in json.loads(
                str(self.connection.send_command("j/workspaces").reply.decode())
            )
        )
        self._active_workspace = json.loads(
            str(self.connection.send_command("j/activeworkspace").reply.decode())
        )["id"]

        for btn in self._buttons_preset:
            self.insert_button(btn)

        for id in open_workspaces:
            if not (btn := self.lookup_or_bake_button(id)):
                continue

            btn.empty = False
            if id == self._active_workspace:
                btn.active = True

            if btn in self._buttons_preset:
                continue

            self.insert_button(btn)
        return

    def on_workspace(self, _, event: HyprlandEvent):
        if len(event.data) < 1:
            return

        active_workspace = int(event.data[0])
        if active_workspace == self._active_workspace:
            return

        if self._active_workspace is not None and (
            old_btn := self._buttons.get(self._active_workspace)
        ):
            old_btn.active = False

        self._active_workspace = active_workspace
        if not (btn := self.lookup_or_bake_button(active_workspace)):
            return

        btn.urgent = False
        btn.active = True

        if btn in self._container.children:
            return
        return self.insert_button(btn)

    def on_createworkspace(self, _, event: HyprlandEvent):
        if len(event.data) < 1:
            return
        new_workspace = int(event.data[0])

        if not (btn := self.lookup_or_bake_button(new_workspace)):
            return

        btn.empty = False
        if btn in self._buttons_preset:
            return
        return self.insert_button(btn)

    def on_destroyworkspace(self, _, event: HyprlandEvent):
        if len(event.data) < 1:
            return

        destroyed_workspace = int(event.data[0])
        if not (btn := self._buttons.get(destroyed_workspace)):
            return  # doens't exist, skip

        btn.active = False
        btn.urgent = False
        btn.empty = True

        if btn in self._buttons_preset:
            return
        return self.remove_button(btn)

    def on_urgent(self, _, event: HyprlandEvent):
        if len(event.data) < 1:
            return

        clients = json.loads(self.connection.send_command("j/clients").reply.decode())
        clients_map = {client["address"]: client for client in clients}
        urgent_client: dict = clients_map.get("0x" + event.data[0], {})
        if not (raw_workspace := urgent_client.get("workspace")):
            return logger.warning(
                f"[Workspaces] received urgent signal, but data received ({event.data[0]}) is uncorrect, skipping..."
            )

        urgent_workspace = int(raw_workspace["id"])
        if not (btn := self._buttons.get(urgent_workspace)):
            return  # doens't exist, skip

        btn.urgent = True
        return logger.info(f"[Workspaces] workspace {urgent_workspace} is now urgent")

    def scroll_handler(self, _, event: Gdk.EventScroll):
        cmd = "" if self._empty_scroll else "e"
        match event.direction:  # type: ignore
            case Gdk.ScrollDirection.UP:
                cmd += "-1" if self._invert_scroll is True else "+1"
                logger.info("[Workspaces] Moving to the next workspace")
            case Gdk.ScrollDirection.DOWN:
                cmd += "+1" if self._invert_scroll is True else "-1"
                logger.info("[Workspaces] Moving to the previous workspace")
            case _:
                return logger.warning(
                    f"[Workspaces] Unknown scroll direction ({event.direction})"  # type: ignore
                )
        return self.connection.send_command(f"batch/dispatch workspace {cmd}")

    def insert_button(self, button: WorkspaceButton) -> None:
        self._buttons[button.id] = button
        self._container.add(button)
        button.connect("clicked", self.do_handle_button_press)
        return self.reorder_buttons()

    def reorder_buttons(self):
        for _, child in sorted(self._buttons.items(), key=lambda i: i[0]):
            self._container.reorder_child(child, (child.id - 1))
        return

    def remove_button(self, button: WorkspaceButton) -> None:
        if self._buttons.pop(button.id, None) is not None:
            self._container.remove(button)
        return button.destroy()

    def lookup_or_bake_button(self, workspace_id: int) -> WorkspaceButton | None:
        if not (btn := self._buttons.get(workspace_id)):
            if self._buttons_factory:
                btn = self._buttons_factory(workspace_id)
        return btn

    def do_handle_button_press(self, button: WorkspaceButton):
        self.connection.send_command(f"batch/dispatch workspace {button.id}")
        return logger.info(f"[Workspaces] Moved to workspace {button.id}")


# TODO: document
class ActiveWindow(Button):
    def __init__(
        self,
        formatter: FormattedString = FormattedString(
            "{'Desktop' if not win_title else truncate(win_title, 42)}",
            truncate=truncate,
        ),
        # TODO: hint super's kwargs
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.connection = get_hyprland_connection()
        self.formatter = formatter

        bulk_connect(
            self.connection,
            {
                "event::activewindow": self.on_activewindow,
                "event::closewindow": self.on_closewindow,
            },
        )

        # all aboard...
        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)

    def on_ready(self, _):
        return self.do_initialize(), logger.info(
            "[ActiveWindow] Connected to the hyprland socket"
        )

    def on_closewindow(self, _, event: HyprlandEvent):
        if len(event.data) < 1:
            return
        return self.do_initialize(), logger.info(
            f"[ActiveWindow] Closed window 0x{event.data[0]}"
        )

    def on_activewindow(self, _, event: HyprlandEvent):
        if len(event.data) < 2:
            return
        return self.set_label(
            self.formatter.format(win_class=event.data[0], win_title=event.data[1])
        ), logger.info(
            f"[ActiveWindow] Activated window {event.data[0]}, {event.data[1]}"
        )

    def do_initialize(self):
        win_data: dict = json.loads(
            self.connection.send_command("j/activewindow").reply.decode()
        )
        win_class = win_data.get("class", "unknown")
        win_title = win_data.get("title", win_class)

        return self.set_label(
            self.formatter.format(win_class=win_class, win_title=win_title)
        )


class Language(Button):
    def __init__(
        self,
        keyboard: str = ".*",
        formatter: FormattedString = FormattedString("{language}"),
        # TODO: hint super's kwargs
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.connection = get_hyprland_connection()
        self.keyboard = keyboard
        self.formatter = formatter

        self.connection.connect("event::activelayout", self.on_activelayout)

        # all aboard...
        if self.connection.ready:
            self.on_ready(None)
        else:
            self.connection.connect("event::ready", self.on_ready)

    def on_ready(self, _):
        return self.do_initialize(), logger.info(
            "[Language] Connected to the hyprland socket"
        )

    def on_activelayout(self, _, event: HyprlandEvent):
        if len(event.data) < 2:
            return logger.warning(
                f"[Language] got invalid event data from hyprland, raw data is\n{event.raw_data}"
            )
        keyboard, language = event.data
        matched: bool = False

        if re.match(self.keyboard, keyboard) and (matched := True):
            self.set_label(self.formatter.format(language=language))

        return logger.debug(
            f"[Language] Keyboard: {keyboard}, Language: {language}, Match: {matched}"
        )

    def do_initialize(self):
        devices: dict[str, list[dict[str, str]]] = json.loads(
            str(self.connection.send_command("j/devices").reply.decode())
        )
        if not devices or not (keyboards := devices.get("keyboards")):
            return logger.warning(
                f"[Language] cound't get devices from hyprctl, gotten data\n{devices}"
            )

        language: str | None = None
        for kb in keyboards:
            if (
                not (kb_name := kb.get("name"))
                or not re.match(self.keyboard, kb_name)
                or not (language := kb.get("active_keymap"))
            ):
                continue

            self.set_label(self.formatter.format(language=language))
            logger.debug(
                f"[Language] found language: {language} for keyboard {kb_name}"
            )
            break

        return (
            logger.info(
                f"[Language] Could not find language for keyboard: {self.keyboard}, gotten keyboards: {keyboards}"
            )
            if not language
            else logger.info(
                f"[Language] Set language: {language} for keyboard: {self.keyboard}"
            )
        )
