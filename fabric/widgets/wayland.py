import gi
import re
import cairo
from enum import Enum
from loguru import logger
from typing import cast, Literal
from collections.abc import Iterable
from fabric.core.service import Property
from fabric.widgets.window import Window
from fabric.utils.helpers import extract_css_values, get_enum_member

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
except:
    raise ImportError(
        "looks like we don't have gtk-layer-shell installed, make sure to install it first (as well as using wayland)"
    )


class WaylandWindowExclusivity(Enum):
    NONE = 1
    "do not reserve any space for this window"
    NORMAL = 2
    "should reserve space for this window"
    AUTO = 3
    "automatically decide whether to reserve space or not"


class WaylandWindow(Window):
    """A wayland specific window for docking purposes (works as a layer)"""

    @Property(
        GtkLayerShell.Layer,
        flags="read-write",
        default_value=GtkLayerShell.Layer.TOP,
    )
    def layer(self) -> GtkLayerShell.Layer:  # type: ignore
        """The layer in which this window sits on

        :return: the layer type for this window
        :rtype: GtkLayerShell.Layer
        """
        return self._layer  # type: ignore

    @layer.setter
    def layer(
        self,
        value: Literal["background", "bottom", "top", "overlay"] | GtkLayerShell.Layer,
    ) -> None:
        self._layer = get_enum_member(
            GtkLayerShell.Layer, value, default=GtkLayerShell.Layer.TOP
        )
        return GtkLayerShell.set_layer(self, self._layer)

    @Property(int, "read-write")
    def monitor(self) -> int:
        """This window's current monitor

        :return: the monitor id of this window
        :rtype: int
        """
        if not (monitor := cast(Gdk.Monitor, GtkLayerShell.get_monitor(self))):
            return -1
        display = monitor.get_display() or Gdk.Display.get_default()
        for i in range(0, display.get_n_monitors()):
            if display.get_monitor(i) is monitor:
                return i
        return -1

    @monitor.setter
    def monitor(self, monitor: int | Gdk.Monitor) -> bool:
        if isinstance(monitor, int):
            display = Gdk.Display().get_default()
            monitor = display.get_monitor(monitor)
        return (
            (GtkLayerShell.set_monitor(self, monitor), True)[1]
            if monitor is not None
            else False
        )

    @Property(WaylandWindowExclusivity, "read-write")
    def exclusivity(self) -> WaylandWindowExclusivity:
        """Exclusivity (space reserving) mode for this window

        :rtype: WaylandWindowExclusivity
        """
        return self._exclusivity

    @exclusivity.setter
    def exclusivity(
        self, value: Literal["none", "normal", "auto"] | WaylandWindowExclusivity
    ) -> None:
        value = get_enum_member(
            WaylandWindowExclusivity, value, default=WaylandWindowExclusivity.NONE
        )
        self._exclusivity = value
        match value:
            case WaylandWindowExclusivity.NORMAL:
                return GtkLayerShell.set_exclusive_zone(self, True)
            case WaylandWindowExclusivity.AUTO:
                return GtkLayerShell.auto_exclusive_zone_enable(self)
            case _:
                return GtkLayerShell.set_exclusive_zone(self, False)

    @Property(bool, "read-write", default_value=False)
    def pass_through(self) -> bool:
        """Whether should this window be pass-through (pass mouse events what's below it) or not

        :rtype: bool
        """
        return self._pass_through

    @pass_through.setter
    def pass_through(self, pass_through: bool = False):
        self._pass_through = pass_through
        region = cairo.Region() if pass_through is True else None
        self.input_shape_combine_region(region)
        del region
        return

    @Property(tuple[GtkLayerShell.Edge, ...], "read-write")
    def anchor(self) -> tuple[GtkLayerShell.Edge, ...]:
        """The list of anchor edges of this window (e.g. "top left bottom")

        :rtype: tuple[GtkLayerShell.Edge, ...]
        """
        return tuple(
            x
            for x in [
                GtkLayerShell.Edge.TOP,
                GtkLayerShell.Edge.RIGHT,
                GtkLayerShell.Edge.BOTTOM,
                GtkLayerShell.Edge.LEFT,
            ]
            if GtkLayerShell.get_anchor(self, x)
        )

    @anchor.setter
    def anchor(self, value: str | Iterable[GtkLayerShell.Edge]) -> None:
        self._anchor = value
        if isinstance(value, (list, tuple)) and all(
            isinstance(edge, GtkLayerShell.Edge) for edge in value
        ):
            for edge in [
                GtkLayerShell.Edge.TOP,
                GtkLayerShell.Edge.RIGHT,
                GtkLayerShell.Edge.BOTTOM,
                GtkLayerShell.Edge.LEFT,
            ]:
                if edge not in value:
                    GtkLayerShell.set_anchor(self, edge, False)
                GtkLayerShell.set_anchor(self, edge, True)
            return
        elif isinstance(value, str):
            for edge, anchored in WaylandWindow.extract_edges_from_string(
                value
            ).items():
                GtkLayerShell.set_anchor(self, edge, anchored)

        return

    @Property(tuple[int, ...], flags="read-write")
    def margin(self) -> tuple[int, ...]:
        """This window's margin (formatted as `(top, right, bottom, left)`)

        :rtype: tuple[int, ...]
        """
        return tuple(
            GtkLayerShell.get_margin(self, x)
            for x in [
                GtkLayerShell.Edge.TOP,
                GtkLayerShell.Edge.RIGHT,
                GtkLayerShell.Edge.BOTTOM,
                GtkLayerShell.Edge.LEFT,
            ]
        )

    @margin.setter
    def margin(self, value: str | Iterable[int]) -> None:
        for edge, mrgv in WaylandWindow.extract_margin(value).items():
            GtkLayerShell.set_margin(self, edge, mrgv)
        return

    @Property(object, "read-write")
    def keyboard_mode(self) -> GtkLayerShell.KeyboardMode:
        """This window's keybaord input mode

        :rtype: GtkLayerShell.KeyboardMode
        """
        kb_mode = GtkLayerShell.get_keyboard_mode(self)
        if GtkLayerShell.get_keyboard_interactivity(self):
            kb_mode = GtkLayerShell.KeyboardMode.EXCLUSIVE
        return kb_mode

    @keyboard_mode.setter
    def keyboard_mode(
        self,
        value: Literal["none", "exclusive", "on-demand"] | GtkLayerShell.KeyboardMode,
    ):
        return GtkLayerShell.set_keyboard_mode(
            self,
            get_enum_member(
                GtkLayerShell.KeyboardMode,
                value,
                default=GtkLayerShell.KeyboardMode.NONE,
            ),
        )

    def __init__(
        self,
        layer: Literal["background", "bottom", "top", "overlay"]
        | GtkLayerShell.Layer = GtkLayerShell.Layer.TOP,
        anchor: str = "",
        margin: str | Iterable[int] = "0px 0px 0px 0px",
        exclusivity: Literal["auto", "normal", "none"]
        | WaylandWindowExclusivity = WaylandWindowExclusivity.NONE,
        keyboard_mode: Literal["none", "exclusive", "on-demand"]
        | GtkLayerShell.KeyboardMode = GtkLayerShell.KeyboardMode.NONE,
        pass_through: bool = False,
        monitor: int | Gdk.Monitor | None = None,
        title: str = "fabric",
        type: Literal["top-level", "popup"] | Gtk.WindowType = Gtk.WindowType.TOPLEVEL,
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
        :param layer: the layer on which this window should sit on, defaults to GtkLayerShell.Layer.TOP
        :type layer: Literal["background", "bottom", "top", "overlay"] | GtkLayerShell.Layer, optional
        :param anchor: anchor edges for this window (e.g. "top right bottom"), defaults to ""
        :type anchor: str, optional
        :param margin: margen values for each edge (in the format of "top right bottom left"), defaults to "0px 0px 0px 0px"
        :type margin: str | Iterable[int], optional
        :param exclusivity: the way should this window reserve its surrounding space, defaults to WaylandWindowExclusivity.NONE
        :type exclusivity: Literal["auto", "normal", "none"] | WaylandWindowExclusivity, optional
        :param keyboard_mode: select the way this window should handle keyboard input, defaults to GtkLayerShell.KeyboardMode.NONE
        :type keyboard_mode: Literal["none", "exclusive", "on-demand"] | GtkLayerShell.KeyboardMode, optional
        :param pass_through: whether to pass mouse events to the below window or not, defaults to False
        :type pass_through: bool, optional
        :param monitor: the monitor in which this window should be displayed at, defaults to None
        :type monitor: int | Gdk.Monitor | None, optional
        :param title: the title of this window (used for window manager scoping), defaults to "fabric"
        :type title: str, optional
        :param type: the type of this window (useful with some window managers), defaults to Gtk.WindowType.TOPLEVEL
        :type type: Literal["top-level", "popup"] | Gtk.WindowType, optional
        :param child: a child widget to add into this window, defaults to None
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
        Window.__init__(
            self,
            title,
            type,
            child,
            name,
            False,
            False,
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
        self._layer = GtkLayerShell.Layer.ENTRY_NUMBER
        self._keyboard_mode = GtkLayerShell.KeyboardMode.NONE
        self._anchor = anchor
        self._exclusivity = WaylandWindowExclusivity.NONE
        self._pass_through = pass_through

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, title)
        self.connect(
            "notify::title",
            lambda *_: GtkLayerShell.set_namespace(self, self.get_title()),
        )
        if monitor is not None:
            self.monitor = monitor
        self.layer = layer
        self.anchor = anchor
        self.margin = margin
        self.keyboard_mode = keyboard_mode
        self.exclusivity = exclusivity
        self.pass_through = pass_through
        self.show_all() if all_visible is True else self.show() if visible is True else None

    def steal_input(self) -> None:
        """Ask the compositor to set this window to have the keyboard interactivity

        .. warning::

            Not guranteed to work with all Wayland compositors!
        """
        return GtkLayerShell.set_keyboard_interactivity(self, True)

    def return_input(self) -> None:
        """Tell the compositor to remove keyboard interactivity from this window"""
        return GtkLayerShell.set_keyboard_interactivity(self, False)

    # custom overrides
    def show(self) -> None:
        super().show()
        return self.do_handle_post_show_request()

    def show_all(self) -> None:
        super().show_all()
        return self.do_handle_post_show_request()

    def do_handle_post_show_request(self) -> None:
        if not self.get_children():
            logger.warning(
                "[WaylandWindow] showing an empty window is not recommended, some compositors might freak out."
            )
        self.pass_through = self._pass_through
        return

    # internals
    @staticmethod
    def extract_anchor_values(string: str) -> tuple[str, ...]:
        """
        Extracts the geometry values from a given geometry string.

        :param string: the string containing the geometry values.
        :type string: str
        :return: a list of unique directions extracted from the geometry string.
        :rtype: list
        """
        direction_map = {"l": "left", "t": "top", "r": "right", "b": "bottom"}
        pattern = re.compile(r"\b(left|right|top|bottom)\b", re.IGNORECASE)
        matches = pattern.findall(string)
        return tuple(set(tuple(direction_map[match.lower()[0]] for match in matches)))

    @staticmethod
    def extract_edges_from_string(string: str) -> dict["GtkLayerShell.Edge", bool]:
        anchor_values = WaylandWindow.extract_anchor_values(string.lower())
        return {
            GtkLayerShell.Edge.TOP: "top" in anchor_values,
            GtkLayerShell.Edge.RIGHT: "right" in anchor_values,
            GtkLayerShell.Edge.BOTTOM: "bottom" in anchor_values,
            GtkLayerShell.Edge.LEFT: "left" in anchor_values,
        }

    @staticmethod
    def extract_margin(input: str | Iterable[int]) -> dict["GtkLayerShell.Edge", int]:
        margins = (
            extract_css_values(input.lower())
            if isinstance(input, str)
            else input
            if isinstance(input, (tuple, list)) and len(input) == 4
            else (0, 0, 0, 0)
        )
        return {
            GtkLayerShell.Edge.TOP: margins[0],
            GtkLayerShell.Edge.RIGHT: margins[1],
            GtkLayerShell.Edge.BOTTOM: margins[2],
            GtkLayerShell.Edge.LEFT: margins[3],
        }
