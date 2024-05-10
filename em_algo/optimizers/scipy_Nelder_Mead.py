"""TODO"""

from typing import Callable
from scipy.optimize import minimize

from em_algo.types import Params
from em_algo.optimizers import AOptimizer


class ScipyNelderMead(AOptimizer):
    """TODO"""

    @property
    def name(self):
        return "ScipyNelder-Mead"

    def minimize(
        self,
        func: Callable[[Params], float],
        params: Params,
    ) -> Params:
        return minimize(func, params, method="Nelder-Mead").x