import os
import re
from collections import defaultdict
from pprint import pprint

import numpy as np
from coffea.util import load
from matplotlib import pyplot as plt

from bucoffea.execute.dataset_definitions import short_name
from bucoffea.helpers.dataset import extract_year, is_data
from bucoffea.helpers.paths import bucoffea_path

pjoin = os.path.join

def acc_from_dir(indir):
    """Load Coffea accumulator from directory with *.coffea files

    :param indir: Directory to search for coffea files
    :type indir: string
    :return: Sum of all found accumulators
    :rtype: dict
    """
    acc = {}
    for file in os.listdir(indir):
        if not file.endswith(".coffea"):
            continue
        acc = acc + load(pjoin(indir, file))
    return acc



def merge_extensions(histogram):
    """Merge extension datasets into one

    :param histogram: The histogram to modify
    :type histogram: Coffea histogram
    :return: Modified histogram
    :rtype: Coffea histogram
    """
    all_datasets = map(str, histogram.identifiers('dataset'))
    mapping = defaultdict(list)
    for d in all_datasets:
        m = re.match('.*(_ext\d+).*', d)
        base = d
        if m:
            base = d.replace(m.groups()[0],"")
        mapping[base].append(d)
    histogram = histogram.group(histogram.axis("dataset"), "dataset", mapping)
    return histogram


def merge_datasets(histogram):
    """Merge datasets that belong same physics process

    :param histogram: The histogram to modify
    :type histogram: Coffea histogram
    :return: Modified histogram
    :rtype: Coffea histogram
    """
    all_datasets = list(map(str, histogram.identifiers('dataset')))
    # TODO:
    #   * Factor mapping out to configuration file?
    #   * Fill in more data sets
    #   * lots of duplicate code (re.match etc) -> simplify
    mapping = {
        'SingleMuon_2017' : [x for x in all_datasets if re.match('SingleMuon_2017[A-Z]+',x)],
        'EGamma_2017' : [x for x in all_datasets if re.match('SingleElectron_2017[A-Z]+',x) or re.match('SinglePhoton_2017[A-Z]+',x)],
        'MET_2017' : [x for x in all_datasets if re.match('MET_2017[A-Z]+',x)],

        'SingleMuon_2018' : [x for x in all_datasets if re.match('SingleMuon_2018[A-Z]+',x)],
        'EGamma_2018' : [x for x in all_datasets if re.match('EGamma_2018[A-Z]+',x)],
        'MET_2018' : [x for x in all_datasets if re.match('MET_2018[A-Z]+',x)],

        'DYNJetsToLL_M-50-MLM_2017' : [x for x in all_datasets if re.match('DY(\d+)JetsToLL_M-50-MLM_2017',x)],
        'DYNJetsToLL_M-50-MLM_2018' : [x for x in all_datasets if re.match('DY(\d+)JetsToLL_M-50-MLM_2018',x)],
        # 'DYJetsToLL_M-50_HT_MLM_2017' : [x for x in all_datasets if re.match('DYJetsToLL_M-50_HT-(\d+)to(\d+)-MLM_2017',x)],
        # 'DYJetsToLL_M-50_HT_MLM_2018' : [x for x in all_datasets if re.match('DYJetsToLL_M-50_HT-(\d+)to(\d+)-MLM_2018',x)],
        # 'ZJetsToNuNu_HT_2017' : [x for x in all_datasets if re.match('ZJetsToNuNu_HT-(\d+)To(\d+)-mg_2017',x)],
        # 'ZJetsToNuNu_HT_2018' : [x for x in all_datasets if re.match('ZJetsToNuNu_HT-(\d+)To(\d+)-mg_2018',x)],
        'WNJetsToLNu-MLM_2017' : [x for x in all_datasets if re.match('W(\d+)JetsToLNu_2017',x)],
        'WNJetsToLNu-MLM_2018' : [x for x in all_datasets if re.match('W(\d+)JetsToLNu_2018',x)]
    }

    # Remove empty lists
    tmp = {}
    for k, v in mapping.items():
        if len(v):
            tmp[k] = v
    mapping = tmp

    # Add datasets we didn't catch yet
    mapped_datasets =  []
    for val in mapping.values():
        mapped_datasets.extend(val)

    for ds in all_datasets:
        if ds in mapped_datasets:
            continue
        else:
            mapping[ds] = [ds]

    # Apply the mapping
    histogram = histogram.group(histogram.axis("dataset"), "dataset", mapping)

    return histogram


def load_xs():

    xsraw = np.loadtxt(bucoffea_path('data/datasets/xs/xs.txt'),dtype=str)
    xs = {}
    for full, val, _, _ in xsraw:
        xs[short_name(full)] = float(val)
    return xs

def lumi(year):
    """Golden JSON luminosity per for given year

    :param year: Year of data taking
    :type year: int
    :return: Golden JSON luminosity for that year in pb (!)
    :rtype: float
    """
    if year==2018:
        return 59.7
    if year==2017:
        return 41.3

def normalize_mc(histogram, acc):
    """MC normalization so that it's ready to compare to data

    :param histogram: Histogram to normalize
    :type histogram: coffea Hist
    :param acc: Accumulator that holds sum-of-weights information
    :type acc: coffea.processor.accumulator
    """
    # Get the list of datasets and filter MC data sets
    datasets = list(map(str, histogram.axis('dataset').identifiers()))

    mcs = [x for x in datasets if not is_data(x)]

    # Normalize to XS * lumi/ sumw
    sumw = acc['sumw']
    xs = load_xs()
    norm_dict = {mc : 1e3 * xs[mc] / sumw[mc] * lumi(extract_year(mc)) for mc in mcs}
    histogram.scale(norm_dict, axis='dataset')

def fig_ratio():
    """Shortcut to create figure with ratio and main panels

    :return: Figure and axes for main and ratio panels
    :rtype: tuple(Figure, axes, axes)
    """
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(7,7), gridspec_kw={"height_ratios": (3, 1)}, sharex=True)
    return fig, ax, rax