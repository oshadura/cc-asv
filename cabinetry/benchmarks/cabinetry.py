import cabinetry
import numpy as np
import uproot


def toy_distribution(noncentral, multiplier, offset, num_events):
    return (
        np.random.noncentral_chisquare(5, noncentral, num_events) * multiplier + offset
    )


def toy_weights(total_yield, num_events):
    avg = total_yield / float(num_events)
    weights = np.random.normal(avg, avg * 0.1, num_events)
    # re-normalize to make sure sum of weights exactly matches avg
    weights *= total_yield / np.sum(weights)
    return weights


def get_samples(num_events):
    dist_s = toy_distribution(10, 12, 350, num_events)
    dist_b = toy_distribution(10, 25, 0, num_events)
    dist_b_var = toy_distribution(12, 30, 0, num_events)
    return [dist_s, dist_b, dist_b_var]


def get_weights(yield_s, yield_b, yield_b_var, num_events):
    w_s = toy_weights(yield_s, num_events)
    w_b = toy_weights(yield_b, num_events)
    w_b_var = toy_weights(yield_b_var, num_events)
    return [w_s, w_b, w_b_var]


def create_pseudodata(yield_s, yield_b):
    # create a dataset with some slightly different composition
    scale_s = 1.2
    scale_b = 1.0
    dist_s = toy_distribution(10, 12, 350, int(yield_s * scale_s))
    dist_b = toy_distribution(10, 25, 0, int(yield_b * scale_b))
    pseudodata = np.hstack((dist_s, dist_b))
    np.random.shuffle(pseudodata)
    return pseudodata


def create_lepton_charge(n_events):
    # lepton charge is +1 or -1 for all events, just to have an extra variable
    charge = (np.random.randint(0, 2, size=n_events) * 2) - 1
    return charge


def create_file(file_name, distributions, weights, labels, *, extra_weights=None):
    if extra_weights is None:
        extra_weights = []
    n_events = len(weights[0])
    with uproot.recreate(file_name) as f:
        # write the predicted processes
        for i, label in enumerate(labels):
            lep_charge = create_lepton_charge(n_events)
            if label == "background":
                f[label] = {
                    "jet_pt": distributions[i],
                    "weight": weights[i],
                    "lep_charge": lep_charge,
                    "weight_up": extra_weights[0],
                    "weight_down": extra_weights[1],
                }
            else:
                f[label] = {
                    "jet_pt": distributions[i],
                    "weight": weights[i],
                    "lep_charge": lep_charge,
                }


def create_file_pseudodata(file_name, pseudodata):
    n_events = len(pseudodata)
    with uproot.recreate(file_name) as f:
        # write pseudodata
        lep_charge = create_lepton_charge(n_events)
        f["pseudodata"] = {"jet_pt": pseudodata, "lep_charge": lep_charge}


def create_input_ntuples():
    # configuration
    num_events = 5000
    yield_s = 125
    yield_b = 1000
    yield_b_var = 1000
    labels = ["signal", "background", "background_varied"]  # names of processes
    file_name = "prediction.root"
    file_name_pseudodata = "data.root"

    np.random.seed(0)

    # distributions for two processes, plus a background uncertainty
    distributions = get_samples(num_events)

    # corresponding weights
    weights = get_weights(yield_s, yield_b, yield_b_var, num_events)

    # weights for an extra background uncertainty
    weight_var_up = (1.2 * (distributions[1] / 350)) * weights[1]
    weight_var_down = (np.ones_like(weight_var_up) * 0.7) * weights[1]

    # create a pseudodataset
    pseudodata = create_pseudodata(yield_s, yield_b)

    # write it all to a file
    create_file(
        file_name,
        distributions,
        weights,
        labels,
        extra_weights=[weight_var_up, weight_var_down],
    )
    create_file_pseudodata(file_name_pseudodata, pseudodata)


class Q1Suite:
    def setup(self):
        self.cabinetry_config = {
            "General": {
                "Measurement": "minimal_example",
                "POI": "Signal_norm",
                "HistogramFolder": "histograms/",
                "InputPath": "{SamplePath}",
            },
            "Regions": [
                {
                    "Name": "Signal_region",
                    "Variable": "jet_pt",
                    "Filter": "lep_charge > 0",
                    "Binning": [300, 400, 500, 600],
                }
            ],
            "Samples": [
                {
                    "Name": "Data",
                    "Tree": "pseudodata",
                    "SamplePath": "data.root",
                    "Data": True,
                },
                {
                    "Name": "Signal",
                    "Tree": "signal",
                    "SamplePath": "prediction.root",
                    "Weight": "weight",
                },
                {
                    "Name": "Background",
                    "Tree": "background",
                    "SamplePath": "prediction.root",
                    "Weight": "weight",
                },
            ],
            "Systematics": [
                {
                    "Name": "Luminosity",
                    "Up": {"Normalization": 0.05},
                    "Down": {"Normalization": -0.05},
                    "Type": "Normalization",
                },
                {
                    "Name": "Modeling",
                    "Up": {
                        "SamplePath": "prediction.root",
                        "Tree": "background_varied",
                    },
                    "Down": {"Symmetrize": True},
                    "Samples": "Background",
                    "Type": "NormPlusShape",
                },
                {
                    "Name": "WeightBasedModeling",
                    "Up": {"Weight": "weight_up"},
                    "Down": {"Weight": "0.7*weight"},
                    "Samples": "Background",
                    "Type": "NormPlusShape",
                },
            ],
            "NormFactors": [
                {
                    "Name": "Signal_norm",
                    "Samples": "Signal",
                    "Nominal": 1,
                    "Bounds": [0, 10],
                }
            ],
        }

        create_input_ntuples()

    def time_build_template(self):
        cabinetry.templates.build(self.cabinetry_config, method="uproot")

    def time_build_template(self):
        cabinetry.templates.build(self.cabinetry_config, method="uproot")
