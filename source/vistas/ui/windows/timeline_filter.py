import datetime

import wx
import wx.adv
import wx.lib.intctrl

from vistas.core.timeline import Timeline
from vistas.ui.events import TimelineEvent
from vistas.ui.utils import post_timeline_change, post_message


class TimeIntervalPanel(wx.Panel):
    """ A control for encapsulating user input for specifying a datetime.timedelta. """

    def __init__(self, parent, id):
        super().__init__(parent, id)

        ctrl_size = wx.Size(20, -1)
        self.days = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY)
        self.days.SetSize(ctrl_size)

        self.seconds = wx.lib.intctrl.IntCtrl(self, wx.ID_ANY)
        self.seconds.SetSize(ctrl_size)

        day_label = wx.StaticText(self, wx.ID_ANY, "Days")
        second_label = wx.StaticText(self, wx.ID_ANY, "Seconds")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        interval_label = wx.StaticText(self, wx.ID_ANY, "Interval Settings")
        main_sizer.Add(interval_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 5)

        grid_sizer = wx.GridSizer(2, 2, 0, 0)
        grid_sizer.Add(day_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.RIGHT, 5)
        grid_sizer.Add(second_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.RIGHT, 5)
        grid_sizer.Add(self.days, 0, wx.BOTTOM, 5)
        grid_sizer.Add(self.seconds, 0, wx.BOTTOM, 5)
        main_sizer.Add(grid_sizer)

        self.UpdateEnabledInputs()

    def UpdateEnabledInputs(self):
        timeline = Timeline.app()
        if timeline.enabled:
            maxstep = timeline.end - timeline.start
            minstep = timeline.min_step
            self.days.Enable(maxstep > datetime.timedelta(1, 0, 0) or datetime.timedelta(1, 0, 0) < minstep)
            self.seconds.Enable(maxstep > datetime.timedelta(0, 1, 0) or datetime.timedelta(1, 0, 0) < minstep)
        else:
            self.days.Disable()
            self.seconds.Disable()

    @property
    def interval(self):
        days = self.days.GetValue()
        seconds = self.seconds.GetValue()
        return datetime.timedelta(days, seconds, 0)

    @interval.setter
    def interval(self, value: datetime.timedelta):
        self.days.ChangeValue(value.days)
        self.seconds.ChangeValue(value.seconds)
        self.UpdateEnabledInputs()


class TimeFilterWindow(wx.Frame):
    """ A window for enabling a user to specify a time filter on the current global timeline. """

    def __init__(self, parent):
        super().__init__(
            parent, wx.ID_ANY, "Timeline Filter",
            style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX | wx.FRAME_FLOAT_ON_PARENT
        )
        timeline = Timeline.app()
        self._filter_has_changed = False

        main_panel = wx.Panel(self, wx.ID_ANY)

        self.start_ctrl = wx.adv.CalendarCtrl(main_panel, wx.ID_ANY, date=wx.pydate2wxdate(timeline.start))
        self.start_ctrl.SetDateRange(wx.pydate2wxdate(timeline.start),
                                     wx.pydate2wxdate(timeline.end))

        self.end_ctrl = wx.adv.CalendarCtrl(main_panel, wx.ID_ANY, date=wx.pydate2wxdate(timeline.end))
        self.end_ctrl.SetDateRange(wx.pydate2wxdate(timeline.start),
                                   wx.pydate2wxdate(timeline.end))

        self.apply_button = wx.Button(main_panel, wx.ID_ANY, "Apply")
        self.apply_button.SetDefault()
        self.reset_button = wx.Button(main_panel, wx.ID_ANY, "Reset")

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(main_sizer)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        main_panel.SetSizer(panel_sizer)

        start_sizer = wx.BoxSizer(wx.VERTICAL)
        start_label = wx.StaticText(main_panel, wx.ID_ANY, "Start Date")
        start_sizer.Add(start_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 10)
        start_sizer.Add(self.start_ctrl)

        end_sizer = wx.BoxSizer(wx.VERTICAL)
        end_label = wx.StaticText(main_panel, wx.ID_ANY, "End Date")
        end_sizer.Add(end_label, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 10)
        end_sizer.Add(self.end_ctrl)

        calendar_sizer = wx.BoxSizer(wx.HORIZONTAL)
        calendar_sizer.Add(start_sizer, 0, wx.EXPAND | wx.RIGHT, 10)
        calendar_sizer.Add(end_sizer, 0, wx.EXPAND | wx.LEFT, 10)
        panel_sizer.Add(calendar_sizer, 0, wx.EXPAND | wx.ALL, 10)

        self.interval_panel = TimeIntervalPanel(main_panel, wx.ID_ANY)
        panel_sizer.Add(self.interval_panel, 0, wx.ALIGN_CENTER_HORIZONTAL)

        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        button_sizer.Add(self.apply_button)
        button_sizer.Add(self.reset_button)
        panel_sizer.Add(button_sizer, 0, wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, 10)

        main_sizer.Add(main_panel, 1, wx.EXPAND)

        self.CenterOnParent()
        self.Fit()

        self.Bind(wx.EVT_SHOW, self.OnShow)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.start_ctrl.Bind(wx.adv.EVT_CALENDAR_SEL_CHANGED, self.OnCalendar)
        self.end_ctrl.Bind(wx.adv.EVT_CALENDAR_SEL_CHANGED, self.OnCalendar)
        self.apply_button.Bind(wx.EVT_BUTTON, self.OnApply)
        self.reset_button.Bind(wx.EVT_BUTTON, self.OnReset)
        self.Refresh()

    def ApplyFilter(self):
        timeline = Timeline.app()
        start = wx.wxdate2pydate(self.start_ctrl.GetDate())
        end = wx.wxdate2pydate(self.end_ctrl.GetDate())
        interval = self.interval_panel.interval
        time_span = timeline.end - timeline.start
        valid_range = start < end
        valid_interval = timeline.min_step <= interval < time_span

        if valid_range and valid_interval and timeline.enabled:
            timeline.filter_start = start
            timeline.filter_end = end
            timeline.filter_interval = interval
            timeline.use_filter = not (timeline.filter_start == timeline.start and
                                            timeline.filter_end == timeline.end and
                                            timeline.filter_interval == timeline.min_step)
            self._filter_has_changed = False
            self.RefreshTimeline()
            self.Refresh()
            return True

        else:
            if not valid_range:
                msg = "Invalid filter range - start date exceeds end date."
            elif not valid_interval:
                msg = "Invalid interval - interval is too large or too small."
            else:
                msg = "Invalid filter - unknown error."
            post_message(msg, 1)
            return False

    def RefreshTimeline(self):
        post_timeline_change(Timeline.app().current, TimelineEvent.VALUE_CHANGED)

    def UpdateFromTimeline(self):
        timeline = Timeline.app()
        self._filter_has_changed = False
        self.start_ctrl.SetDateRange(wx.pydate2wxdate(timeline.start),
                                     wx.pydate2wxdate(timeline.end))
        self.start_ctrl.SetDate(wx.pydate2wxdate(timeline.filter_start))
        self.end_ctrl.SetDateRange(wx.pydate2wxdate(timeline.start),
                                   wx.pydate2wxdate(timeline.end))
        self.end_ctrl.SetDate(wx.pydate2wxdate(timeline.filter_end))
        self.interval_panel.interval = timeline.filter_interval
        self.Refresh()

    def OnShow(self, event):
        self.UpdateFromTimeline()
        event.Skip()

    def OnClose(self, event):
        if self._filter_has_changed:
            md = wx.MessageDialog(self, "You have unapplied filter settings. Would you like to apply them?",
                                  "Apply Filter Options?", style=wx.YES_NO)
            if md.ShowModal() == wx.ID_YES and not self.ApplyFilter():
                return
        self.Hide()

    def OnCalendar(self, event):
        self._filter_has_changed = True
        event.Skip()

    def OnApply(self, event):
        self.ApplyFilter()

    def OnReset(self, event):
        # Reset timeline filter to start and finish
        timeline = Timeline.app()
        timeline.filter_start = timeline.start
        timeline.filter_end = timeline.end
        timeline.filter_interval = timeline.min_step
        self.interval_panel.interval = timeline.filter_interval
        self._filter_has_changed = False
        self.RefreshTimeline()
        self.Refresh()
