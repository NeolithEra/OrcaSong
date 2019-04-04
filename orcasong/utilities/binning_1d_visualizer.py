#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
For investigating the ideal binning, based on the info in calibrated
.h5 files.

Specialized classes TimePlotter and ZPlotter are available for plotting
the time/ Z-Coordinate.

"""

import numpy as np
import km3pipe as kp
import matplotlib.pyplot as plt


class FieldPlotter:
    """
    Baseclass for investigating the ideal binning, based on the info in
    a field of calibrated .h5 files.

    Intended for 1d binning, like for fields "time" or "pos_z".
    Workflow:
    1. Initialize with files, then run .plot() to extract and store
       the data, and show the plot interactively.
    2. Choose a binning via .set_binning.
    3. Run .plot() again to show the plot with the adjusted binning on the
       stored data.
    4. Repeat step 2 and 3 unitl happy with binning.
    (5.) Save plot via .plot(savepath), or get the bin edges via .get_bin_edges()

    The plot will have some bins attached in both directions for
    better overview.

    Attributes:
    -----------
    files : list or str
        The .h5 file(s).
    field : str
        The field to look stuff up, e.g. "time", "pos_z", ...
    filter_for_du : int, optional
        Only get hits from one specific du, specified by the int.
    hits : ndarray
        The extracted Hits.
    mc_hits : ndarray
        The extracted McHits, if present.
    n_events : int
        The number of events in the extracted data.
    limits : List
        Left- and right-most edge of the binning.
    n_bins : int
        The number of bins.
    plot_padding : List
        Fraction of bins to append to left and right direction
        (only in the plot for better overview).
    x_label : str
        X label of the plot.
    y_label : str
        Y label of the plot.
    hist_kwargs : dict
        Kwargs for plt.hist
    xlim : List
        The xlimits of the hist plot.
    show_plots : bool
        If True, auto plt.show() the plot.

    """
    def __init__(self, files, field):
        self.files = files
        self.field = field
        self.filter_for_du = None

        self.hits = None
        self.mc_hits = None
        self.n_events = None

        self.limits = None
        self.n_bins = 100
        self.plot_padding = [0.2, 0.2]

        # Plotting stuff
        self.xlabel = None
        self.ylabel = 'Fraction of hits'
        self.hist_kwargs = {
            "histtype": "stepfilled",
            "density": True,
        }
        self.xlim = None
        self.ylim = None
        self.show_plots = True
        self.last_ylim = None

    def plot(self, only_mc_hits=False, save_path=None):
        """
        Generate and store or load the data, then make the plot.

        Parameters
        ----------
        only_mc_hits : bool
            If true, plot the McHits instead of the Hits.
        save_path : str, optional
            Save plot to here.

        Returns
        -------
        fig, ax : pyplot figure
            The plot.

        """
        if self.hits is None:
            self.extract()
        fig, ax = self.make_histogram(only_mc_hits, save_path)
        return fig, ax

    def set_binning(self, limits, n_bins):
        """
        Set the desired binning.

        Parameters
        ----------
        limits : List
            Left- and right-most edge of the binning.
        n_bins : int
            The number of bins.

        """
        self.limits = limits
        self.n_bins = n_bins

    def get_binning(self):
        """
        Set the desired binning.

        Returns
        -------
        limits : List
            Left- and right-most edge of the binning.
        n_bins : int
            The number of bins.

        """
        return self.limits, self.n_bins

    def get_bin_edges(self):
        """
        Get the bin edges as a ndarray.

        """
        limits, n_bins = self.get_binning()

        if limits is None:
            raise ValueError("Can not return bin edges: No binning limits set")

        bin_edges = np.linspace(limits[0], limits[1], n_bins + 1)

        return bin_edges

    def extract(self):
        """
        Extract the content of a field from all events in the file(s) and
        store it.

        """
        data_all_events = None
        mc_all_events = None
        self.n_events = 0

        if not isinstance(self.files, list):
            files = [self.files]
        else:
            files = self.files

        event_pump = kp.io.hdf5.HDF5Pump(filenames=files)

        for i, event_blob in enumerate(event_pump):
            self.n_events += 1

            if i % 2000 == 0:
                print("Blob no. "+str(i))

            data_one_event = self._get_hits(event_blob, get_mc_hits=False)

            if data_all_events is None:
                data_all_events = data_one_event
            else:
                data_all_events = np.concatenate(
                    [data_all_events, data_one_event], axis=0)

            if "McHits" in event_blob:
                mc_one_event = self._get_hits(event_blob, get_mc_hits=True)

                if mc_all_events is None:
                    mc_all_events = mc_one_event
                else:
                    mc_all_events = np.concatenate(
                        [mc_all_events, mc_one_event], axis=0)

        event_pump.close()

        print("Number of events: " + str(self.n_events))

        self.hits = data_all_events
        self.mc_hits = mc_all_events

    def make_histogram(self, only_mc_hits=False, save_path=None):
        """
        Plot the hist data. Can also save it if given a save path.

        Parameters
        ----------
        only_mc_hits : bool
            If true, plot the McHits instead of the Hits.
        save_path : str, optional
            Save the fig to this path.

        Returns
        -------
        fig, ax : pyplot figure
            The plot.

        """
        if only_mc_hits:
            data = self.mc_hits
        else:
            data = self.hits

        if data is None:
            raise ValueError("Can not make histogram, no data extracted yet.")

        bin_edges = self._get_padded_bin_edges()

        fig, ax = plt.subplots()
        n, bins, patches = plt.hist(data, bins=bin_edges, **self.hist_kwargs)
        print("Size of first bin: " + str(bins[1] - bins[0]))

        plt.grid(True, zorder=0, linestyle='dotted')

        if self.limits is not None:
            for bin_line_x in self.limits:
                plt.axvline(x=bin_line_x, color='firebrick', linestyle='--')

        if self.xlabel is None:
            plt.xlabel(self._get_xlabel())

        if self.xlim is not None:
            plt.xlim(self.xlim)

        if self.ylim is not None:
            plt.ylim(self.ylim)

        plt.ylabel(self.ylabel)
        plt.tight_layout()

        if save_path is not None:
            print("Saving plot to "+str(save_path))
            plt.savefig(save_path)

        if self.show_plots:
            plt.show()

        return fig, ax

    def _get_padded_bin_edges(self):
        """
        Get the padded bin edges.

        """
        limits, n_bins = self.get_binning()

        if limits is None:
            bin_edges = n_bins

        else:
            total_range = limits[1] - limits[0]
            bin_size = total_range / n_bins

            addtnl_bins = [
                int(self.plot_padding[0] * n_bins),
                int(self.plot_padding[1] * n_bins)
            ]

            padded_range = [
                limits[0] - bin_size * addtnl_bins[0],
                limits[1] + bin_size * addtnl_bins[1]
            ]
            padded_n_bins = n_bins + addtnl_bins[0] + addtnl_bins[1]
            bin_edges = np.linspace(padded_range[0], padded_range[1],
                                    padded_n_bins + 1)

        return bin_edges

    def _get_hits(self, blob, get_mc_hits):
        """
        Get desired attribute from an event blob.

        Parameters
        ----------
        blob
            The blob.
        get_mc_hits : bool
            If true, will get the "McHits" instead of the "Hits".

        Returns
        -------
        blob_data : ndarray
            The data.

        """
        if get_mc_hits:
            field_name = "McHits"
        else:
            field_name = "Hits"

        blob_data = blob[field_name][self.field]

        if self.filter_for_du is not None:
            dus = blob[field_name]["du"]
            blob_data = blob_data[dus == self.filter_for_du]

        return blob_data

    def _get_xlabel(self):
        """
        Some saved xlabels.

        """
        if self.field == "time":
            xlabel = "Time [ns]"
        elif self.field == "pos_z":
            xlabel = "Z position [m]"
        else:
            xlabel = None
        return xlabel

    def __repr__(self):
        return "<FieldPlotter: {}>".format(self.files)


class TimePreproc(kp.Module):
    """
    Preprocess the time in the blob.

    t0 will be added to the time for real data, but not simulations.
    Time hits and mchits will be shifted by the time of the first triggered hit.

    """
    def configure(self):
        self.correct_hits = self.get('correct_hits', default=True)
        self.correct_mchits = self.get('correct_mchits', default=True)

    def process(self, blob):
        blob = time_preproc(blob, self.correct_hits, self.correct_mchits)
        return blob


def time_preproc(blob, correct_hits=True, correct_mchits=True):
    """
    Preprocess the time in the blob.

    t0 will be added to the time for real data, but not simulations.
    Time hits and mchits will be shifted by the time of the first triggered hit.

    """
    hits_time = blob["Hits"].time

    if "McHits" not in blob:
        # add t0 only for real data, not sims
        hits_t0 = blob["Hits"].t0
        hits_time = np.add(hits_time, hits_t0)

    hits_triggered = blob["Hits"].triggered
    t_first_trigger = np.min(hits_time[hits_triggered == 1])

    if correct_hits:
        blob["Hits"].time = np.subtract(hits_time, t_first_trigger)

    if correct_mchits:
        mchits_time = blob["McHits"].time
        blob["McHits"].time = np.subtract(mchits_time, t_first_trigger)

    return blob


class TimePlotter(FieldPlotter):
    """
    For plotting the time.
    """
    def __init__(self, files):
        field = "time"
        FieldPlotter.__init__(self, files, field)

    def _get_hits(self, blob, get_mc_hits):
        blob = time_preproc(blob)

        if get_mc_hits:
            field_name = "McHits"
        else:
            field_name = "Hits"

        blob_data = blob[field_name][self.field]

        if self.filter_for_du is not None:
            dus = blob[field_name]["du"]
            blob_data = blob_data[dus == self.filter_for_du]

        return blob_data


class ZPlotter(FieldPlotter):
    """
    For plotting the z dim.
    """
    def __init__(self, files):
        field = "pos_z"
        FieldPlotter.__init__(self, files, field)

        self.plotting_bins = 100

    def _get_padded_bin_edges(self):
        """
        Get the padded bin edges.

        """
        return self.plotting_bins

    def set_binning(self, limits, n_bins):
        """
        Set the desired binning.

        Parameters
        ----------
        limits : List
            Left- and right-most edge of the binning.
        n_bins : int
            The number of bins.

        """
        bin_edges = np.linspace(limits[0], limits[1],
                                n_bins + 1)
        self.limits = bin_edges
        self.n_bins = n_bins

    def get_bin_edges(self):
        return self.limits
