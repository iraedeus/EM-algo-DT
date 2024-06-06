"""Module which contains functions for transform example experiment results into pd database"""

import itertools

import pandas as pd
import numpy as np


from tqdm.contrib.concurrent import process_map

from em_algo.types import Samples
from em_algo.distribution_mixture import DistributionMixture, DistributionInMixture

from examples.utils import SingleSolverResult, TestResult
from examples.mono_test_generator import Clicker
from examples.config import MAX_WORKERS


def nll(samples: Samples, mixture: DistributionMixture) -> float:
    """Mean least squares logarithm metric"""
    occur = sum(np.log(mixture.pdf(x)) for x in samples) / len(samples)
    if occur == -0.0:
        occur = 0.0
    return occur


def identity_guessing_chance(
    dx: DistributionMixture, dy: DistributionMixture, sample: Samples
):
    """Identity guessing chance metric"""

    dxs = list(dx)
    dxs.sort(key=lambda x: x.params[0])

    dys = list(dy)
    dys.sort(key=lambda x: x.params[0])

    success = 0

    for x in sample:
        if ((dxs[0].pdf(x) > dxs[1].pdf(x)) and (dys[0].pdf(x) > dys[1].pdf(x))) or (
            (dxs[0].pdf(x) < dxs[1].pdf(x)) and (dys[0].pdf(x) < dys[1].pdf(x))
        ):
            success += 1

    return success / len(sample)


def result_to_df_diff(result: SingleSolverResult):
    """Diff test result mapper"""

    gaussian_start_params = [(0.0, 3.0), (-10.0, 3.0), (10.0, 3.0)]
    weibull_start_params = [(0.5, 1.0), (1.0, 1.0), (1.5, 1.0), (5.0, 1.0)]
    sizes = [50, 100, 200, 500, 1000]
    tests_per_cond = 4
    tests_per_size = 8

    clicker = Clicker()

    dct = {}

    for sp in gaussian_start_params:
        for second_sp in np.linspace(sp[0] - 5, sp[0] + 5, num=8, endpoint=True):
            for _ in sizes:
                for _ in range(tests_per_cond):
                    for _ in range(tests_per_size):
                        dct[clicker.click()] = (sp[0], second_sp)

    for sp in weibull_start_params:
        for second_sp in np.linspace(
            max(sp[0] - 5, 0.1), sp[0] + 5, num=8, endpoint=True
        ):
            for _ in sizes:
                for _ in range(tests_per_cond):
                    for _ in range(tests_per_size):
                        dct[clicker.click()] = (sp[0], second_sp)

    distribution_mixture = DistributionMixture(
        [
            (
                d
                if (d.prior_probability is not None) and (d.prior_probability > 0.001)
                else DistributionInMixture(d.model, d.params, None)
            )
            for d in result.result.content
        ]
    )
    failed = all(d.prior_probability is None for d in result.result.content)

    start = dct[result.test.index][0]
    diff = dct[result.test.index][1]

    return {
        "test_index": result.test.index,
        "optimizer": result.solver.optimizer.name,
        "k": len(result.test.true_mixture),
        "sample": result.test.problem.samples,
        "true_mixture": result.test.true_mixture,
        "result_mixture": distribution_mixture,
        "error": result.result.error,
        "log": result.log,
        "steps": result.steps,
        "time": result.time,
        "model": result.test.true_mixture[0].model.name,
        "size": len(result.test.problem.samples),
        "success": (result.steps < 128) and not failed,
        "failed": failed,
        "occur": nll(result.test.all_data, distribution_mixture),
        "start": start,
        "diff": diff,
        "res_err": identity_guessing_chance(
            result.test.true_mixture, result.result.content, result.test.all_data
        ),
    }


def prepare_diff(results: list[TestResult]):
    """Diff test result mapper"""

    return pd.DataFrame(
        process_map(
            result_to_df_diff,
            list(itertools.chain.from_iterable(result.results for result in results)),
            max_workers=MAX_WORKERS,
            chunksize=256,
        )
    )


def result_to_df(result: SingleSolverResult):
    """Mono test result mapper"""

    distribution_mixture = DistributionMixture(
        [
            (
                d
                if (d.prior_probability is not None) and (d.prior_probability > 0.001)
                else DistributionInMixture(d.model, d.params, None)
            )
            for d in result.result.content
        ]
    )
    failed = all(d.prior_probability is None for d in result.result.content)

    return {
        "test_index": result.test.index,
        "optimizer": result.solver.optimizer.name,
        "k": len(result.test.true_mixture),
        "sample": result.test.problem.samples,
        "true_mixture": result.test.true_mixture,
        "result_mixture": distribution_mixture,
        "error": result.result.error,
        "log": result.log,
        "steps": result.steps,
        "time": result.time,
        "model": result.test.true_mixture[0].model.name,
        "size": len(result.test.problem.samples),
        "success": (result.steps < 16) and failed,
        "failed": failed,
        "occur": nll(result.test.all_data, distribution_mixture),
    }


def prepare(results: list[TestResult]):
    """Mono test result mapper"""

    return pd.DataFrame(
        process_map(
            result_to_df,
            list(itertools.chain.from_iterable(result.results for result in results)),
            max_workers=MAX_WORKERS,
            chunksize=256,
        )
    )
