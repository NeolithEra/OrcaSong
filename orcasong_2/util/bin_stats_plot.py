"""
Functions for plotting the bin stats made by the BinningStatsMaker module.
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import h5py
import numpy as np
import argparse

__author__ = 'Stefan Reck'


def plot_hists(hists, save_to, plot_bin_edges=True):
    """
    Plot histograms made by the BinningStatsMaker to the given pdf path.

    Parameters
    ----------
    hists : dict or List
        Dicts with the info about the binning, generated by the BinningStatsMaker.
        Can also be a list of dicts (for multiple files), which will be
        combined to one plot.
    save_to : str
        Where to save the plot to.
    plot_bin_edges : bool
        If true, will plot the bin edges as horizontal lines. Is never used
        for the time binning (field name "time").

    """
    if isinstance(hists, list):
        hists = combine_hists(hists)

    with PdfPages(save_to) as pdf_file:
        for bin_name, hists_data in hists.items():
            hist_bin_edges = hists_data["hist_bin_edges"]
            bin_edges = hists_data["bin_edges"]
            hist = hists_data["hist"]
            cut_off = hists_data["cut_off"]
            total_hits = np.sum(hist) + np.sum(cut_off)

            bin_widths = np.diff(hist_bin_edges)
            hist_prob = hist / bin_widths / np.sum(hist)

            fig, ax = plt.subplots()
            plt.bar(hist_bin_edges[:-1],
                    hist_prob,
                    align="edge",
                    width=bin_widths
                    )

            if plot_bin_edges and bin_name != "time":
                for bin_edge in bin_edges:
                    plt.axvline(x=bin_edge, color='grey', linestyle='-',
                                linewidth=1, alpha=0.9)

            # place a text box in upper left in axes coords
            out_neg_rel = cut_off[0] / total_hits
            out_pos_rel = cut_off[1] / total_hits
            textstr = "Hits cut off:\nLeft: {:.1%}\n" \
                      "Right: {:.1%}".format(out_neg_rel, out_pos_rel)
            props = dict(boxstyle='round', facecolor='white', alpha=0.9)
            ax.text(0.95, 0.95, textstr, transform=ax.transAxes,
                    verticalalignment='top', bbox=props,
                    horizontalalignment="right")

            # the auto ticks are nice even numbers
            ylims = [0, ax.get_yticks().max()]
            ax.set_ylim(ylims)

            plt.xlabel(bin_name)
            plt.ylabel("Density of hits")

            pdf_file.savefig(fig)

    print("Saved binning plot to " + save_to)


def combine_hists(hists_list):
    """
    Combine the hists for multiple files into a single big one.

    Parameters
    ----------
    hists_list : List
        A list of dicts (hists from the BinningStatsMaker for different files).

    Returns
    -------
    combined_hists : Dict
        The combined hist.

    """
    # initialize combined dict according to first dict in list
    combined_hists = {}
    for bin_name, hists_data in hists_list[0].items():
        hist_bin_edges = hists_data["hist_bin_edges"]
        bin_edges = hists_data["bin_edges"]
        bin_name = bin_name

        combined_hists[bin_name] = {
            "hist": np.zeros(len(hist_bin_edges) - 1),
            "hist_bin_edges": hist_bin_edges,
            "bin_edges": bin_edges,
            # below smallest edge, above largest edge:
            "cut_off": np.zeros(2),
        }

    # add them together
    for hists in hists_list:
        for bin_name, hists_data in hists.items():
            # name and bin edges must be the same for all hists
            if bin_name not in combined_hists:
                raise NameError(
                    "Hists dont all have the same binning field name:"
                    "{}".format(bin_name))

            bin_edges = hists_data["bin_edges"]
            comb_edges = combined_hists[bin_name]["bin_edges"]
            if len(bin_edges) != len(comb_edges):
                raise ValueError("Hists have different hist bin edges: {} vs {}"
                                 .format(bin_edges, comb_edges))

            hist_bin_edges = hists_data["hist_bin_edges"]
            comb_hist_edges = combined_hists[bin_name]["hist_bin_edges"]
            if len(hist_bin_edges) != len(comb_hist_edges):
                raise ValueError("Hists have different bin edges: {} vs {}"
                                 .format(hist_bin_edges, comb_hist_edges))

            combined_hists[bin_name]["hist"] += hists_data["hist"]
            combined_hists[bin_name]["cut_off"] += hists_data["cut_off"]

    return combined_hists


def add_hists_to_h5file(hists, file):
    """
    Add the binning stats as groups to a h5 file.

    Parameters
    ----------
    hists : dict
        The histst from the BinningStatsMaker module.
    file : str
        Path to the h5 file.

    """
    base_name = "bin_stats/"
    with h5py.File(file, "a") as f:
        for bin_name, hists_data in hists.items():
            for key, val in hists_data.items():
                h5_folder = base_name + bin_name + "/" + key
                f.create_dataset(h5_folder, data=val)


def plot_hist_of_files(files, save_as):
    """
    Plot the binning stats of a list of files.

    Parameters
    ----------
    files : List
        Path of the files as str.
    save_as : str
        Where to save the plot to.

    """
    hists_list = []
    opened_files = []

    try:
        for i, file in enumerate(files):
            if i % 100 == 0:
                print("File {} of {}..." .format(i, len(files)))

            f = h5py.File(file, "r")
            if "bin_stats/" not in f:
                raise ValueError("Can not plot: File does not have bin_stats")
            hists_list.append(f["bin_stats/"])
            opened_files.append(f)

        print("Plotting...")
        plot_hists(hists_list, save_as)

    finally:
        print("Closing files...")
        for file in opened_files:
            file.close()


def main():
    parser = argparse.ArgumentParser(description='Plot the bin stats in h5 files')
    parser.add_argument('save_as', metavar='S', type=str,
                        help='Where to save the plot to.')
    parser.add_argument('files', metavar='F', type=str, nargs='+',
                        help='The files')

    args = parser.parse_args()
    plot_hist_of_files(args.files, args.save_as)


if __name__ == "__main__":
    main()