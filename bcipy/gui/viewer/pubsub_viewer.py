# pylint: disable=no-name-in-module,no-member,wrong-import-position,ungrouped-imports
"""
EEG viewer that uses the pubsub pattern to retrieve data.
"""
import csv
import logging
import time
from queue import Empty, Queue

import matplotlib
import numpy as np
import wx
from wx.lib.pubsub import pub
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.pyplot import NullFormatter, NullLocator

from bcipy.acquisition.device_info import DeviceInfo
from bcipy.acquisition.util import StoppableProcess, StoppableThread
from bcipy.gui.viewer.launcher import Launcher
from bcipy.gui.viewer.ring_buffer import RingBuffer
from bcipy.gui.viewer.filter import downsample_filter, sig_pro_filter

logging.basicConfig(level=logging.DEBUG,
                    format='(%(threadName)-9s) %(message)s',)

MSG_CHANNEL = "eeg_listener"
CMD_CHANNEL = "command_channel"
STOP_CMD = "stop"


class DataPublisher(StoppableThread):
    """Continuously reads data from the data queue and publishes it using
    wx pubsub. Pubsub only works from the same Thread, but Queues can be used
    by multiple processes. This class provides an adapter to allow the pubsub
    semantics across threads."""

    def __init__(self, data_queue):
        super(DataPublisher, self).__init__()
        self.data_queue = data_queue
        self.wait = 0.1

    def run(self):
        """Continuously reads data from the queue and published it.
        Once data has been received it expects a continous flow and stops the
        thread if data is no longer available."""

        logging.debug("Starting EEG Viewer DataPublisher.")
        attempts = 0
        while self.running():
            try:
                data = self.data_queue.get(True, self.wait)
                pub.sendMessage(MSG_CHANNEL, msg=data)
                self.data_queue.task_done()
                attempts = 0
            except Empty:
                attempts += 1
                if attempts > 5:
                    logging.debug(("Max attempts to retrieve data exceeded.",
                                   "Stopping DataPublisher"))
                    pub.sendMessage(CMD_CHANNEL, msg=STOP_CMD)
                    return
                time.sleep(0.1)

        logging.debug("Stopping EEG Viewer DataPublisher.")


class EegFrame(wx.Frame):
    """GUI Frame in which data is plotted. Plots a subplot for every channel.
    Relies on the data producer to determine the rate at which data is displayed.

    Parameters:
    -----------
        data_queue - data source
        device_info - metadata about the data.
        seconds - how many seconds worth of data to display.
        downsample_factor - how much to compress the data. A factor of 1
            displays the raw data.
        refresh - time in milliseconds; how often to refresh the plots
    """

    def __init__(self, data_queue, device_info: DeviceInfo,
                 seconds: int = 2, downsample_factor: int = 2,
                 refresh: int = 500):
        wx.Frame.__init__(self, None, -1,
                          'EEG Viewer', size=(800, 550))

        self.publisher = DataPublisher(data_queue)
        pub.subscribe(self.data_listener, MSG_CHANNEL)
        pub.subscribe(self.command_listener, CMD_CHANNEL)

        self.refresh_rate = refresh
        self.samples_per_second = device_info.fs
        self.records_per_refresh = int(
            (self.refresh_rate / 1000) * self.samples_per_second)

        self.channels = device_info.channels
        self.removed_channels = ['TRG', 'timestamp']
        self.data_indices = self.init_data_indices()

        self.seconds = seconds
        self.downsample_factor = downsample_factor
        self.filter = downsample_filter(downsample_factor, device_info.fs)
        self.buffer = self.init_buffer()

        # figure size is in inches.
        self.figure = Figure(figsize=(12, 9), dpi=80, tight_layout=True)
        self.axes = self.init_axes()

        self.canvas = FigureCanvas(self, -1, self.figure)
        self.Bind(wx.EVT_CLOSE, self.shutdown)

        self.CreateStatusBar()

        # Toolbar
        self.toolbar = wx.BoxSizer(wx.VERTICAL)
        self.start_stop_btn = wx.Button(self, -1, "Start")

        self.Bind(wx.EVT_BUTTON, self.toggle_stream, self.start_stop_btn)

        self.sigpro_checkbox = wx.CheckBox(self, label="Filtered")
        self.sigpro_checkbox.SetValue(False)
        self.Bind(wx.EVT_CHECKBOX, self.toggle_filtering_handler,
                  self.sigpro_checkbox)

        controls = wx.BoxSizer(wx.HORIZONTAL)
        controls.Add(self.start_stop_btn, 1, wx.ALIGN_CENTER, 0)
        controls.Add(self.sigpro_checkbox, 1, wx.ALIGN_CENTER, 0)

        self.toolbar.Add(controls, 1, wx.ALIGN_CENTER, 0)
        self.init_channel_buttons()

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.EXPAND)
        sizer.Add(self.toolbar, 0, wx.ALIGN_BOTTOM | wx. ALIGN_CENTER)
        self.SetSizer(sizer)
        self.SetAutoLayout(1)
        self.Fit()

        self.init_data()
        self.started = False
        self.start()
        self.i = 0
        self.publisher.start()

    def data_listener(self, msg):
        """Listens for published data and updates the underling display data.
        Refreshes the display at the provided interval."""

        self.buffer.append(msg)
        self.i += 1

        if self.started and self.i % self.records_per_refresh == 0:
            self.update_view(None)

    def command_listener(self, msg):
        """Listens for commands issued through pubsub."""
        if msg == STOP_CMD:
            self.stop()

    def init_data_indices(self):
        return [i for i in range(len(self.channels))
                if self.channels[i] not in self.removed_channels
                and 'TRG' not in self.channels[i]]

    def init_buffer(self):
        """Initialize the buffer"""
        buf_size = int(self.samples_per_second * self.seconds)
        empty_val = [0.0 for _x in self.channels]
        return RingBuffer(buf_size, pre_allocated=True, empty_value=empty_val)

    def init_axes(self):
        """Sets configuration for axes"""
        axes = self.figure.subplots(len(self.data_indices), 1, sharex=True)
        for i, channel in enumerate(self.data_indices):
            ch_name = self.channels[channel]
            axes[i].set_frame_on(False)
            axes[i].set_ylabel(ch_name, rotation=0, labelpad=15)
            axes[i].yaxis.set_major_locator(NullLocator())
            axes[i].xaxis.set_major_formatter(NullFormatter())
            axes[i].yaxis.set_major_formatter(NullFormatter())
            axes[i].grid()
        return axes

    def reset_axes(self):
        """Clear the data in the gui."""
        self.figure.clear()
        self.axes = self.init_axes()

    def init_channel_buttons(self):
        """Add buttons for toggling the channels."""

        channel_box = wx.BoxSizer(wx.HORIZONTAL)
        for channel_index in self.data_indices:
            channel = self.channels[channel_index]
            chkbox = wx.CheckBox(self, label=channel, id=channel_index)
            chkbox.SetValue(channel not in self.removed_channels)

            self.Bind(wx.EVT_CHECKBOX, self.toggle_channel, chkbox)
            channel_box.Add(chkbox, 0, wx.ALIGN_CENTER, 0)

        self.toolbar.Add(channel_box, 1, wx.ALIGN_LEFT, 0)

    def toggle_channel(self, event):
        """Remove the provided channel from the display"""
        channel_index = event.GetEventObject().GetId()
        channel = self.channels[channel_index]

        previously_running = self.started
        if self.started:
            self.stop()

        if channel in self.removed_channels:
            self.removed_channels.remove(channel)
        else:
            self.removed_channels.append(channel)
        self.data_indices = self.init_data_indices()
        self.reset_axes()
        self.init_data()
        self.canvas.draw()
        if previously_running:
            self.start()

    def start(self):
        """Start streaming data in the viewer."""
        self.started = True
        self.start_stop_btn.SetLabel("Pause")

    def stop(self):
        """Stop/Pause the viewer."""
        self.started = False
        self.start_stop_btn.SetLabel("Start")

    def shutdown(self, _event):
        """Handler for when a user closes the window."""
        self.stop()
        self.publisher.stop()
        self.Destroy()

    def toggle_stream(self, _event):
        """Toggle data streaming"""
        if self.started:
            self.stop()
        else:
            self.start()

    def toggle_filtering_handler(self, event):
        """Event handler for toggling data filtering."""
        self.with_refresh(self.toggle_filtering)

    def toggle_filtering(self):
        """Toggles data filtering."""
        if self.sigpro_checkbox.GetValue():
            self.filter = sig_pro_filter(
                self.downsample_factor, self.samples_per_second)
        else:
            self.filter = downsample_filter(
                self.downsample_factor, self.samples_per_second)

    def with_refresh(self, fn):
        """Performs the given action and refreshes the display."""
        previously_running = self.started
        if self.started:
            self.stop()
        fn()
        # re-initialize
        self.reset_axes()
        self.init_data()
        if previously_running:
            self.start()

    def current_data(self):
        """Returns the data as an np array with a row of floats for each
        displayed channel."""

        # array of 'object'; TRG data may be strings
        data = np.array(self.buffer.get())

        # select only data columns and convert to float
        return np.array(data[:, self.data_indices], dtype='float64').transpose()

    def init_data(self):
        """Initialize the data."""
        channel_data = self.filter(self.current_data())

        for i, _channel in enumerate(self.data_indices):
            data = channel_data[i].tolist()
            self.axes[i].plot(data, linewidth=0.8)

    def update_view(self, _evt):
        """Called by the data listener."""
        channel_data = self.filter(self.current_data())

        # plot each channel
        for i, _channel in enumerate(self.data_indices):
            data = channel_data[i].tolist()
            self.axes[i].lines[0].set_ydata(data)
            self.axes[i].set_ybound(lower=min(data), upper=max(data))

        if self.started:
            self.canvas.draw()


def Viewer(data_queue: Queue, device_info: DeviceInfo) -> StoppableProcess:
    """Creates an EEG Viewer that can be started and stopped.
    Returns:
    --------
        a StoppableProcess
    """
    return Launcher(EegFrame, data_queue=data_queue, device_info=device_info)


def main(data_file: str, seconds: int, downsample: int, refresh: int):
    """Run the viewer gui

    Parameters:
    -----------
        data_file - raw_data.csv file to stream.
        seconds - how many seconds worth of data to display.
        downsample - how much the data is downsampled. A factor of 1
            displays the raw data.
    """
    from bcipy.gui.viewer.file_streamer import FileStreamer

    # read metadata
    with open(data_file) as csvfile:
        name = next(csvfile).strip().split(",")[-1]
        freq = float(next(csvfile).strip().split(",")[-1])

        reader = csv.reader(csvfile)
        channels = next(reader)

    app = wx.App(False)
    queue = Queue()
    streamer = FileStreamer(data_file, queue)
    streamer.start()
    frame = EegFrame(queue, DeviceInfo(fs=freq, channels=channels, name=name),
                     seconds, downsample, refresh)
    frame.Show(True)
    app.MainLoop()
    streamer.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f', '--file', help='path to the data file', default='raw_data.csv')
    parser.add_argument('-s', '--seconds',
                        help='seconds to display', default=2, type=int)
    parser.add_argument('-d', '--downsample',
                        help='downsample factor', default=2, type=int)
    parser.add_argument('-r', '--refresh',
                        help='refresh rate in ms', default=500, type=int)

    args = parser.parse_args()
    main(args.file, args.seconds, args.downsample, args.refresh)
