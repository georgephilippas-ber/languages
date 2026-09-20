from typing import List, Any
from numpy.random import default_rng

generator_ = default_rng()


def weighted_sample(items: List[Any], weights: List[float] | None):

    return generator_.choice(items, p=weights)

if __name__ == "__main__":
    print(weighted_sample([1, 2, 3],None))
