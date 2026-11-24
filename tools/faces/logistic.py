"""Bayesian logistic regression (numpy only), which learns both the dev's taste and the sexes from his answers.

Each answer is a row x with a target t from 0 to 1, the chance it gives that sigmoid(w . x) answers yes.
The prior on w is normal with independent weights. The posterior is the Laplace approximation at its mode.
"""
import math
import numpy as np

PROBIT = 1.7                                   # sigmoid(x) is close to Phi(x / PROBIT)
BALD_C = np.sqrt(np.pi * np.log(2) / 2)
ERF = np.vectorize(math.erf, otypes=[float])


def shape_prior(share, sd):
    """Prior variances of weights on the face model's coefficients that are isotropic in shape: in proportion
    to the share of the variance each component explains, so that w . c has standard deviation sd over faces
    whose coefficients are unit normal."""
    return share / share.sum() * sd ** 2


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def cosine(a, b):
    return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-300))


class Posterior:
    """Normal approximation to the posterior of w given rows x (N, P) and targets t (N,): mean, cov."""

    def __init__(self, prior_var, x, t, steps=30):
        x = np.asarray(x, float).reshape(-1, len(prior_var))
        t = np.broadcast_to(np.asarray(t, float), len(x))
        precision0 = np.diag(1.0 / prior_var)
        w = np.zeros(len(prior_var))
        for _ in range(steps):
            p = sigmoid(x @ w)
            hessian = precision0 + (x * (p * (1.0 - p))[:, None]).T @ x
            step = np.linalg.solve(hessian, x.T @ (t - p) - precision0 @ w)
            w += step
            if np.abs(step).max() < 1e-9:
                break
        p = sigmoid(x @ w)
        self.mean = w
        self.cov = np.linalg.inv(precision0 + (x * (p * (1.0 - p))[:, None]).T @ x)

    def logit(self, x):
        """Mean and variance of w . x for rows x (..., P)."""
        return x @ self.mean, np.einsum("...i,ij,...j->...", x, self.cov, x)

    def information(self, x):
        """Expected information, in bits, an answer on each row x gives about w (BALD)."""
        mean, var = self.logit(x)
        mean, var = mean / PROBIT, var / PROBIT ** 2
        p = 0.5 * (1.0 + ERF(mean / np.sqrt(2.0 * (1.0 + var))))
        entropy = -(p * np.log2(np.clip(p, 1e-12, 1)) + (1 - p) * np.log2(np.clip(1 - p, 1e-12, 1)))
        return entropy - BALD_C / np.sqrt(var + BALD_C ** 2) * np.exp(-mean ** 2 / (2 * (var + BALD_C ** 2)))

    def settled(self, rng, part=slice(None), draws=400):
        """Expected cosine between the weights in `part` and their mean: 0 knows nothing of their direction,
        1 knows it exactly."""
        mean = self.mean[part]
        return float(np.mean([cosine(w, mean) for w in rng.multivariate_normal(self.mean, self.cov, draws)[:, part]]))
