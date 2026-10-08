from typing import List, Any
from numpy.random import default_rng

generator_ = default_rng()


def sample_weighted(items: List[Any], k: int, weights: List[float] | None):
    if weights is not None and sum(weights) > 0:
        normalized_weights_ = [i_ / sum(weights) for i_ in weights]
    else:
        normalized_weights_ = None

    return generator_.choice(items, k, p=normalized_weights_)


if __name__ == "__main__":
    pass
