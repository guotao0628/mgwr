#Bandwidth optimization methods

__author__ = "Taylor Oshan"

import numpy as np
from copy import deepcopy
import copy
from collections import namedtuple

def golden_section(a, c, delta, function, tol, max_iter, int_score=False, multi=True):
    """
    Golden section search routine
    Method: p212, 9.6.4
    Fotheringham, A. S., Brunsdon, C., & Charlton, M. (2002).
    Geographically weighted regression: the analysis of spatially varying relationships.

    Parameters
    ----------
    a               : float
                      initial max search section value
    b               : float
                      initial min search section value
    delta           : float
                      constant used to determine width of search sections
    function        : function
                      obejective function to be evaluated at different section
                      values
    int_score       : boolean
                      False for float score, True for integer score
    tol             : float
                      tolerance used to determine convergence
    max_iter        : integer
                      maximum iterations if no convergence to tolerance

    Returns
    -------
    opt_val         : float
                      optimal value
    opt_score       : kernel
                      optimal score
    output          : list of tuples
                      searching history
    """
    b = a + delta * np.abs(c-a)
    d = c - delta * np.abs(c-a)
    score = 0.0
    diff = 1.0e9
    iters  = 0
    output = []
    dict = {}
    while np.abs(diff) > tol and iters < max_iter:
        iters += 1
        if int_score:
            b = np.round(b)
            d = np.round(d)
        
        if b in dict:
            score_b = dict[b]
        else:
            score_b = function(b)
            if multi == False:
                print("Bandwidth: ",np.round(b, 2), ", score: ", "{0:.2f}".format(np.array(score_b).flatten()[0]))
            dict[b] = score_b
        
        if d in dict:
            score_d = dict[d]
        else:
            score_d = function(d)
            if multi == False:
                print("Bandwidth: ",np.round(d, 2), ", score: ", "{0:.2f}".format(np.array(score_d).flatten()[0]))
            dict[d] = score_d

        if score_b <= score_d:
            opt_val = b
            opt_score = score_b
            c = d
            d = b
            b = a + delta * np.abs(c-a)

        else:
            opt_val = d
            opt_score = score_d
            a = b
            b = d
            d = c - delta * np.abs(c-a)
        print(opt_score)
        output.append((opt_val, opt_score))
        diff = score_b - score_d
        score = opt_score

    return np.round(opt_val, 2), opt_score, output

def equal_interval(l_bound, u_bound, interval, function, int_score=False,multi=True):
    """
    Interval search, using interval as stepsize

    Parameters
    ----------
    l_bound         : float
                      initial min search section value
    u_bound         : float
                      initial max search section value
    interval        : float
                      constant used to determine width of search sections
    function        : function
                      obejective function to be evaluated at different section
                      values
    int_score       : boolean
                      False for float score, True for integer score

    Returns
    -------
    opt_val         : float
                      optimal value
    opt_score       : kernel
                      optimal score
    output          : list of tuples
                      searching history
    """
    a = l_bound
    c = u_bound
    b = a + interval
    if int_score:
        a = np.round(a,0)
        c = np.round(c,0)
        b = np.round(b,0)

    output = []

    score_a = function(a)
    if multi == False:
        print("Bandwidth:",a,", score:", "{0:.2f}".format(np.array(score_a).flatten()[0]))
    score_c = function(c)
    if multi == False:
        print("Bandwidth:",c,", score:", "{0:.2f}".format(np.array(score_c).flatten()[0]))

    output.append((a,score_a))
    output.append((c,score_c))

    if score_a < score_c:
        opt_val = a
        opt_score = score_a
    else:
        opt_val = c
        opt_score = score_c

    while b < c:
        score_b = function(b)
        print("Bandwidth:",b,", score:", "{0:.2f}".format(np.array(score_b).flatten()[0]))
        output.append((b,score_b))

        if score_b < opt_score:
            opt_val = b
            opt_score = score_b
        b = b + interval

    return opt_val, opt_score, output

def multi_bw(init, y, X, n, k, family, tol, max_iter, rss_score,
        gwr_func, bw_func, sel_func, multi_bw_min, multi_bw_max):
    """
    Multiscale GWR bandwidth search procedure using iterative GAM backfitting
    """
    if init is None:
        bw = sel_func(bw_func(y, X))
        optim_model = gwr_func(y, X, bw)
    else:
        optim_model = gwr_func(y, X, init)
    bw_gwr = bw
    err = optim_model.resid_response.reshape((-1,1))
    param = optim_model.params

    XB = np.multiply(param, X)
    if rss_score:
        rss = np.sum((err)**2)
    iters = 0
    scores = []
    delta = 1e6
    BWs = []
    bw_counter = np.zeros(k)
    bws = np.empty(k)

    for iters in range(1, max_iter+1):
        new_XB = np.zeros_like(X)
        vals = []
        params = np.zeros_like(X)
        f_XB = XB.copy()
        f_err = err.copy()
        
        for j in range(k):
            temp_y = XB[:,j].reshape((-1,1))
            temp_y = temp_y + err
            temp_X = X[:,j].reshape((-1,1))
            bw_class = bw_func(temp_y, temp_X)
            
            if np.all(bw_counter==2):
                bw = bws[j]
            else:
                bw = sel_func(bw_class, multi_bw_min[j], multi_bw_max[j])
                if bw == bws[j]:
                    bw_counter[j] += 1
                else:
                    bw_counter = np.zeros(k)
        
            optim_model = gwr_func(temp_y, temp_X, bw)
            err = optim_model.resid_response.reshape((-1,1))
            param = optim_model.params.reshape((-1,))
            new_XB[:,j] = optim_model.predy.reshape(-1)
            params[:,j] = param
            bws[j] = bw

        num = np.sum((new_XB - XB)**2)/n
        den = np.sum(np.sum(new_XB, axis=1)**2)
        score = (num/den)**0.5
        XB = new_XB

        if rss_score:
            predy = np.sum(np.multiply(params, X), axis=1).reshape((-1,1))
            new_rss = np.sum((y - predy)**2)
            score = np.abs((new_rss - rss)/new_rss)
            rss = new_rss
        scores.append(copy.deepcopy(score))
        delta = score
        BWs.append(copy.deepcopy(bws))

        print("Iteration",iters,"SOC:", np.round(score,7))
        print("Bandwidths:", ', '.join([str(bw) for bw in bws]))
        if delta < tol:
            break

    opt_bws = BWs[-1]
    return (opt_bws, np.array(BWs),
                          np.array(scores), params,
                          err, bw_gwr)
