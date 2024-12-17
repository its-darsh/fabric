import gi
import math
import cairo
from typing import Literal, Iterable
from fabric.core.service import Property
from fabric.widgets.widget import Widget
from fabric.utils.helpers import get_enum_member, clamp

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk


# TODO: reimplement `angle` and `gap_size` in a better way
class CircularProgressBar(Gtk.DrawingArea, Widget):
    @Property(float, "read-write", default_value=0.0)
    def min_value(self) -> float:
        """Minimum value for this progress bar

        :rtype: float
        """
        return self._min_value

    @min_value.setter
    def min_value(self, value: float):
        self._min_value = clamp(value, self.min_value, self.max_value)
        return self.queue_draw()

    @Property(float, "read-write", default_value=1.0)
    def max_value(self) -> float:
        """Maximum value for this progress bar

        :rtype: float
        """
        return self._max_value

    @max_value.setter
    def max_value(self, value: float):
        if value == 0:
            raise ValueError("max_value cannot be zero")
        self._max_value = value
        return self.queue_draw()

    @Property(float, "read-write", default_value=1.0)
    def value(self) -> float:
        """The value this progress bar is currently holding

        :rtype: float
        """
        return self._value

    @value.setter
    def value(self, value: float):
        self._value = value
        return self.queue_draw()

    @Property(bool, "read-write", default_value=False)
    def pie(self) -> bool:
        """Whether should this progress bar be displayed in the shape of a _pie_ or not

        :rtype: bool
        """
        return self._pie

    @pie.setter
    def pie(self, value: bool):
        self._pie = value
        return self.queue_draw()

    @Property(int, "read-write", default_value=4)
    def line_width(self) -> int:
        """
        The width of this progress bar's value highlight

        .. tip::
            The CSS property `border-width` will act same as this property

        :return: progress's fill width (in pixels)
        :rtype: int
        """
        return self._line_width

    @line_width.setter
    def line_width(self, value: int):
        self._line_width = value
        return self.queue_draw()

    @Property(object, "read-write")
    def line_style(self) -> cairo.LineCap:
        """The shape of the ends of the value highlight

        **Possible values**:
        - `cairo.LineCap.BUTT`,`None` and `"none"`: do not add extra line ends
        - `cairo.LineCap.ROUND` (`"round"`): add rounded caps for each end
        - `cairo.LineCap.SQUARE` (`"square"`): (looks janky in the usecase of this class) add boxy caps to each end


        .. image:: https://www.cairographics.org/samples/set_line_cap.png
            :alt: an image showing the difference between different line style, types from right to left list as butt (or none), round and square


        :rtype: cairo.LineCap
        """
        return self._line_style  # type: ignore

    @line_style.setter
    def line_style(
        self,
        line_style: Literal["none", "butt", "round", "square"] | cairo.LineCap,
    ):
        self._line_style = get_enum_member(
            cairo.LineCap,  # type: ignore
            line_style,  # type: ignore
            default=cairo.LineCap.BUTT,
        )
        return self.queue_draw()

    # @Property(int, "read-write")
    # def angle(self) -> int:
    #     return self._angle

    # @angle.setter
    # def angle(self, value: int):
    #     self._angle = value
    #     return self.queue_draw()

    # @Property(int, "read-write")
    # def gap_size(self) -> int:
    #     return self._gap_size

    # @gap_size.setter
    # def gap_size(self, value: int):
    #     self._gap_size = value
    #     return self.queue_draw()

    def __init__(
        self,
        value: float = 1.0,
        min_value: float = 0.0,
        max_value: float = 1.0,
        line_width: int = 4,
        line_style: Literal["none", "butt", "round", "square"]
        | cairo.LineCap = cairo.LineCap.ROUND,
        pie: bool = False,
        # angle: int = 0,
        # gap_size: int = 0,
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
        :param value: the default value to initialize this progress bar with, defaults to 1.0
        :type value: float, optional
        :param min_value: the minimum value this progress bar can reach, defaults to 0.0
        :type min_value: float, optional
        :param max_value: the maximum value this progress bar can reach, defaults to 1.0
        :type max_value: float, optional
        :param line_width: the width of this progress bar's value highlight (in pixels), you can set this property via the CSS property `border-width`, defaults to 4
        :type line_width: int, optional
        :param line_style: the style of this progress bar's value highlight, defaults to cairo.LineCap.ROUND
        :type line_style: Literal["none", "butt", "round", "square"] | cairo.LineCap, optional
        :param pie: whether should draw this progress bar in a "pie" shape, defaults to False
        :type pie: bool, optional
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
        Gtk.DrawingArea.__init__(self)  # type: ignore
        Widget.__init__(
            self,
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
        self._value: float = 1.0
        self._min_value: float = 0.0
        self._max_value: float = 1.0
        self._line_width: int = 4
        self._line_style: cairo.LineCap = cairo.LineCap.ROUND
        self._pie: bool = False
        self._angle: int = 0
        self._gap_size: int = 0

        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.line_width = line_width
        self.line_style = line_style
        self.pie = pie
        # self.angle = angle
        # self.gap_size = gap_size

        self.connect("draw", self.on_draw)

    def do_calculate_radius(self):
        width = self.get_allocated_width() / 2
        height = (self.get_allocated_height() / 2) - 1
        return int(min(width, height))

    def do_calculate_diameter(self):
        return 2 * self.do_calculate_radius()

    def do_calculate_perferred_size(self):
        d = self.do_calculate_diameter()
        if d > self.get_allocation().width:  # type: ignore
            natural = d
        else:
            natural = self.get_allocation().width  # type: ignore
        return d, natural

    def do_get_preferred_width(self):
        return self.do_calculate_perferred_size()

    def do_get_preferred_height(self):
        return self.do_calculate_perferred_size()

    def on_draw(self, _, cr: cairo.Context):
        # CSS properties lookup table
        #  -------------------------------
        # | border: ... COLOR SIZE        |
        #  -------------------------------
        # | will result in SIZE begin     |
        # | used as the line_width value  |
        # | and COLOR begin used as the   |
        # | color of the progress         |
        #  -------------------------------
        # | background fill     | background-color
        # |---------------------|--------
        # | radius fill         | color
        # |---------------------|--------
        # | progress fill       | border-color
        # |---------------------|--------
        # | progress line width | border-width
        #  ------------------------------

        cr.save()
        cr.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        style_context = self.get_style_context()
        border = style_context.get_border(Gtk.StateFlags.BACKDROP)
        background_color = style_context.get_background_color(Gtk.StateFlags.NORMAL)
        radius_color = style_context.get_color(Gtk.StateFlags.NORMAL)
        progress_color = style_context.get_border_color(Gtk.StateFlags.NORMAL)

        line_width = max(
            self._line_width,
            border.top,  # type: ignore
            border.bottom,  # type: ignore
            border.left,  # type: ignore
            border.right,  # type: ignore
            style_context.get_property("min-width", Gtk.StateFlags.NORMAL),  # type: ignore
            style_context.get_property("min-height", Gtk.StateFlags.NORMAL),  # type: ignore
        )

        # doing the math
        delta = 0
        center_x = self.get_allocated_width() / 2
        center_y = self.get_allocated_height() / 2
        radius = self.do_calculate_radius()
        d = radius - line_width
        delta = radius - line_width / 2
        if d < 0:
            delta = 0
            line_width = radius

        cr.set_line_cap(self._line_style)
        cr.set_line_width(line_width)

        # background fill
        Gdk.cairo_set_source_rgba(cr, background_color)  # type: ignore
        cr.arc(center_x, center_y, delta + (line_width / 2), 0, 2 * math.pi)
        cr.fill()

        # radius
        Gdk.cairo_set_source_rgba(cr, radius_color)  # type: ignore
        cr.move_to(center_x, center_y) if self._pie is True else None
        cr.arc(
            center_x,
            center_y,
            delta + (self._line_width / 2) if self._pie is True else delta,
            0,
            (2 * math.pi),
        )
        cr.fill() if self._pie is True else cr.stroke()

        # progress
        Gdk.cairo_set_source_rgba(cr, progress_color)  # type: ignore
        cr.move_to(center_x, center_y) if self._pie is True else None
        cr.arc(
            center_x,
            center_y,
            delta + (self._line_width / 2) if self._pie is True else delta,
            0 + (1.5 * math.pi),
            0 + (1.5 + (self._value / self._max_value) * 2) * math.pi,
        )
        cr.fill() if self._pie is True else cr.stroke()

        cr.restore()
