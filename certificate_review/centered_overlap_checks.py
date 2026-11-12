"""Independent exact rational half-plane clipping checks; CPU standard library."""
from fractions import Fraction as F


def clip(poly, a, b, bound):
    """Intersect with a*x+b*y <= bound, retaining boundary points."""
    out = []
    for p, q in zip(poly, poly[1:]+poly[:1]):
        vp, vq = a*p[0]+b*p[1]-bound, a*q[0]+b*q[1]-bound
        if (vp <= 0) != (vq <= 0):
            r = vp/(vp-vq)
            out.append((p[0]+r*(q[0]-p[0]), p[1]+r*(q[1]-p[1])))
        if vq <= 0:
            out.append(q)
    return out


def intersection_area(eps, t, shift=(F(0), F(0))):
    c, s = (1-t*t)/(1+t*t), 2*t/(1+t*t)
    poly = [(-F(1, 2), -eps/2), (F(1, 2), -eps/2),
            (F(1, 2), eps/2), (-F(1, 2), eps/2)]
    x, y = shift
    for a, b, bound in ((c, s, F(1, 2)), (-c, -s, F(1, 2)),
                         (-s, c, eps/2), (s, -c, eps/2)):
        poly = clip(poly, a, b, bound+a*x+b*y)
        if not poly:
            return F(0)
    return abs(sum(p[0]*q[1]-p[1]*q[0] for p, q in zip(poly, poly[1:]+poly[:1])))/2


def formula(eps, t):
    if t == 0:
        return eps
    if t >= eps:
        return eps*eps*(1+t*t)/(2*t)
    return (1+t*t)*(2*eps-(1+eps*eps)*t)/(2*(1-t*t))


def original_formula(eps, t):
    if t == 0:
        return eps
    c, s = (1-t*t)/(1+t*t), 2*t/(1+t*t)
    if t >= eps:
        return eps*eps/s
    return eps-((c+eps*s-1)**2+(s+eps*c-eps)**2)/(4*s*c)


if __name__ == '__main__':
    eps_values = {F(1, n) for n in range(1, 21)} | {F(1, 200), F(2, 3), F(3, 4), F(99, 100)}
    t_values = {F(a, b) for b in range(1, 21) for a in range(b+1)}
    centered = translated = 0
    for eps in sorted(eps_values):
        for t in sorted(t_values | {eps}):
            exact = intersection_area(eps, t)
            assert exact == formula(eps, t), (eps, t, exact, formula(eps, t))
            assert exact == original_formula(eps, t), (eps, t)
            centered += 1
    for eps in (F(1, 200), F(1, 20), F(1, 2), F(1)):
        for t in (F(0), eps/2, eps, (1+eps)/2, F(1)):
            for x in (F(-1), F(-1, 4), F(0), F(1, 4), F(1)):
                for y in (-eps, -eps/4, F(0), eps/4, eps):
                    area = intersection_area(eps, t, (x, y))
                    assert area <= formula(eps, t), (eps, t, x, y)
                    translated += 1
    print('exact centered clipping/formula comparisons:', centered)
    print('translated-area <= centered-area comparisons:', translated)
    print('eps=1, phi=pi/2:', intersection_area(F(1), F(1)))
