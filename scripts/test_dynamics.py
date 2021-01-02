import numpy as np
import jax
import jax.numpy as jnp
import sympy as sym
from functools import partial
import IPython

Mb = 3
M1 = 2
M2 = 1

LX = 0
LY = 0
L1 = 1
L2 = 0.5

I1 = M1 * L1**2 / 12
I2 = M2 * L2**2 / 12

G = 9.8


def symbolic_dynamics(time):
    t = sym.symbols('t')
    q = sym.Matrix([sym.Function('q1')(t), sym.Function('q2')(t), sym.Function('q3')(t)])
    dq = q.diff(t)

    x1 = q[0] + LX + 0.5*L1*sym.cos(q[1])
    y1 = LY + 0.5*L1*sym.sin(q[1])
    x2 = q[0] + LX + L1*sym.cos(q[1]) + 0.5*L2*sym.cos(q[1]+q[2])
    y2 = LY + L1*sym.sin(q[1]) + 0.5*L2*sym.sin(q[1]+q[2])

    dx1 = x1.diff(t)
    dy1 = y1.diff(t)
    dx2 = x2.diff(t)
    dy2 = y2.diff(t)

    # Potential energy
    Pb = 0
    P1 = M1*G*y1
    P2 = M2*G*y2
    P = Pb + P1 + P2

    # Kinetic energy
    Kb = 0.5*Mb*dq[0]**2
    K1 = 0.5*M1*(dx1**2+dy1**2) + 0.5*I1*dq[1]**2
    K2 = 0.5*M2*(dx2**2+dy2**2) + 0.5*I2*dq[2]**2
    K = Kb + K1 + K2

    # Lagrangian
    L = K - P

    # Generalized forces
    tau = L.diff(dq).diff(t) - L.diff(q)

    return tau.subs({
        q[0]: sym.sin(t),
        q[1]: t,
        q[2]: t*t,
        t: time}).doit()


def configuration(t, np=np):
    ''' Define joint configuration as function of time. '''
    q = np.array([np.sin(t), t, t*t])
    return q


def manual_dynamics(q, dq, ddq):
    xb, θ1, θ2 = q
    dxb, dθ1, dθ2 = dq
    ddxb, ddθ1, ddθ2 = ddq

    θ12 = θ1 + θ2
    dθ12 = dθ1 + dθ2
    ddθ12 = ddθ1 + ddθ2

    dPbdq = np.zeros(3)
    dP1dq = np.array([0, 0.5*M1*G*L1*np.cos(θ1), 0])
    dP2dq = np.array([0, M2*G*(L1*np.cos(θ1)+0.5*L2*np.cos(θ12)),
                      0.5*M2*G*L2*np.cos(θ12)])

    dKbdq = np.zeros(3)
    dK1dq = np.array([0, -0.5*M1*L1*dθ1*dxb*np.cos(θ1), 0])
    dK2dq = np.array([
        0,
        -M2*(L1*dxb*dθ1*np.cos(θ1) + 0.5*L2*dxb*dθ12*np.cos(θ12)),
        -0.5*M2*L2*dθ12*(L1*dθ1*np.sin(θ2) + dxb*np.cos(θ12))])

    ddt_dKbddq = np.array([Mb*ddxb, 0, 0])
    ddt_dK1ddq = np.array([
        M1*ddxb - 0.5*M1*L1*(ddθ1*np.sin(θ1)+dθ1**2*np.cos(θ1)),
        -0.5*M1*L1*(ddxb*np.sin(θ1)+dxb*dθ1*np.cos(θ1)) + (0.25*M1*L1**2*ddθ1
                                                           + I1*ddθ1),
        0])
    ddt_dK2ddq = np.array([
        0.5*M2*(2*ddxb - 2*L1*(ddθ1*np.sin(θ1)+dθ1**2*np.cos(θ1))
                - L2*(ddθ12*np.sin(θ12)+dθ12**2*np.cos(θ12))),
        0.5*M2*((2*L1**2+0.5*L2**2+2*L1*L2*np.cos(θ2))*ddθ1
                - 2*L1*L2*dθ1*dθ2*np.sin(θ2)
                + (0.5*L2**2+L1*L2*np.cos(θ2))*ddθ2
                - L1*L2*dθ2**2*np.sin(θ2)
                - (2*L1*np.sin(θ1)+L2*np.sin(θ12))*ddxb
                - 2*L1*dxb*dθ1*np.cos(θ1)
                - L2*dxb*dθ12*np.cos(θ12)),
        0.5*M2*((0.5*L2**2+L1*L2*np.cos(θ2))*ddθ1 - L1*L2*dθ1*dθ2*np.sin(θ2)
                - L2*(ddxb*np.sin(θ12)+dxb*dθ12*np.cos(θ12)) + 0.5*L2**2*ddθ2) + I2*ddθ2])

    dPdq = dPbdq + dP1dq + dP2dq
    dKdq = dKbdq + dK1dq + dK2dq
    ddt_dKddq = ddt_dKbddq + ddt_dK1ddq + ddt_dK2ddq
    tau = ddt_dKddq - dKdq + dPdq

    return tau


def calc_mass_matrix(q, np=np):
    xb, θ1, θ2 = q
    θ12 = θ1 + θ2

    m11 = Mb + M1 + M2
    m12 = -(0.5*M1+M2)*L1*np.sin(θ1) - 0.5*M2*L2*np.sin(θ12)
    m13 = -0.5*M2*L2*np.sin(θ12)

    m22 = (0.25*M1+M2)*L1**2 + 0.25*M2*L2**2 + M2*L1*L2*np.cos(θ2) + I1
    m23 = 0.5*M2*L2*(0.5*L2+L1*np.cos(θ2))

    m33 = 0.25*M2*L2**2 + I2

    M = np.array([
        [m11, m12, m13],
        [m12, m22, m23],
        [m13, m23, m33]])
    return M


def calc_gravity_vector(q):
    xb, θ1, θ2 = q
    θ12 = θ1 + θ2
    return np.array([0,
                     (0.5*M1+M2)*G*L1*np.cos(θ1) + 0.5*M2*L2*G*np.cos(θ12),
                     0.5*M2*L2*G*np.cos(θ12)])


def manual_dynamics_mat(q, dq, ddq):
    xb, θ1, θ2 = q
    dxb, dθ1, dθ2 = dq

    θ12 = θ1 + θ2
    dθ12 = dθ1 + dθ2

    M = calc_mass_matrix(q)
    g = calc_gravity_vector(q)

    c11 = 0
    c12 = -(0.5*M1+M2)*L1*dθ1*np.cos(θ1) - 0.5*M2*L2*(dθ1+2*dθ2)*np.cos(θ12)
    c13 = -0.5*M2*L2*(dθ2+2*dθ1)*np.cos(θ12)

    c21 = -(M1+2*M2)*L1*dθ1*np.cos(θ1) - M2*L2*dθ12*np.cos(θ12)
    c22 = -(M1+2*M2)*L1*dxb*np.cos(θ1) - M2*L2*dxb*np.cos(θ12) - M2*L1*L2*dθ2*np.sin(θ2)
    c23 = -M2*L2*dxb*np.cos(θ12) - 0.5*M2*L1*L2*dθ2*np.sin(θ2)

    c31 = -M2*L2*dθ12*np.cos(θ12)
    c32 = -M2*L1*L2*np.sin(θ2)*(0.5*dθ1+dθ2) - M2*L2*dxb*np.cos(θ12)
    c33 = -M2*L2*(L1*dθ1*np.sin(θ2) + dxb*np.cos(θ12))

    C = np.array([
        [c11, c12, c13],
        [c21, c22, c23],
        [c31, c32, c33]])

    return M.dot(ddq) + C.dot(dq) + g


def potential_energy(q, np=np):
    y1 = LY + 0.5*L1*np.sin(q[1])
    y2 = LY + L1*np.sin(q[1]) + 0.5*L2*np.sin(q[1]+q[2])

    Pb = 0
    P1 = M1*G*y1
    P2 = M2*G*y2
    P = Pb + P1 + P2

    return P


# def body_points(t, np=np):
#     q = configuration(t)
#
#     x1 = q[0] + LX + 0.5*L1*np.cos(q[1])
#     y1 = LY + 0.5*L1*np.sin(q[1])
#     x2 = q[0] + LX + L1*np.cos(q[1]) + 0.5*L2*np.cos(q[1]+q[2])
#     y2 = LY + L1*np.sin(q[1]) + 0.5*L2*np.sin(q[1]+q[2])
#
#     return np.array([x1, y1, x2, y2])


def kinetic_energy(q, dq, np=np):
    # x1 = q[0] + LX + 0.5*L1*np.cos(q[1])
    # y1 = LY + 0.5*L1*np.sin(q[1])
    # x2 = q[0] + LX + L1*np.cos(q[1]) + 0.5*L2*np.cos(q[1]+q[2])
    # y2 = LY + L1*np.sin(q[1]) + 0.5*L2*np.sin(q[1]+q[2])

    # TODO can we auto-diff these?
    # TODO this should be done with Jacobian calculations (i.e. linear in dq)
    dx1 = dq[0] - 0.5*L1*dq[1]*np.sin(q[1])
    dy1 = 0.5*L1*dq[1]*np.cos(q[1])
    dx2 = dq[0] - L1*dq[1]*np.sin(q[1]) - 0.5*L2*(dq[1]+dq[2])*np.sin(q[1]+q[2])
    dy2 = L1*dq[1]*np.cos(q[1]) + 0.5*L2*(dq[1]+dq[2])*np.cos(q[1]+q[2])

    Kb = 0.5*Mb*dq[0]**2
    K1 = 0.5*M1*(dx1**2+dy1**2) + 0.5*I1*dq[1]**2
    K2 = 0.5*M2*(dx2**2+dy2**2) + 0.5*I2*dq[2]**2

    return Kb + K1 + K2


def lagrangian(q, dq, np=np):
    K = kinetic_energy(q, dq, np=np)
    P = potential_energy(q, np=np)
    return K - P


def auto_diff_dynamics():
    q_func = partial(configuration, np=jnp)
    dq_func = jax.jacfwd(partial(configuration, np=jnp))

    # diff Lagrangian w.r.t. q
    dLdq_func = jax.grad(partial(lagrangian, np=jnp), argnums=0)

    # diff Lagrangian w.r.t. dq
    dLddq_func = jax.grad(partial(lagrangian, np=jnp), argnums=1)

    # compose to make dLdq a function of time t
    def dLddq_func_t(t):
        return dLddq_func(q_func(t), dq_func(t))

    # diff dLdq w.r.t. t
    ddt_dLddq_func_t = jax.jacfwd(dLddq_func_t)

    # generalized forces expressed as a function of time
    def tau_func(t):
        q = q_func(t)
        dq = dq_func(t)
        return ddt_dLddq_func_t(t) - dLdq_func(q, dq)

    return jax.jit(tau_func)


def main():
    tau_func = auto_diff_dynamics()

    q_func = partial(configuration, np=jnp)
    dq_func = jax.jit(jax.jacfwd(partial(configuration, np=jnp)))
    ddq_func = jax.jit(jax.jacfwd(dq_func))

    t = 1.0
    q = q_func(t)
    dq = dq_func(t)
    ddq = ddq_func(t)

    dMdq_func = jax.jacfwd(partial(calc_mass_matrix, np=jnp))
    M = calc_mass_matrix(q)
    g = calc_gravity_vector(q)
    dMdq = dMdq_func(q)


    print(tau_func(t))
    print(np.array(symbolic_dynamics(t)).astype(np.float64).flatten())
    print(manual_dynamics(q, dq, ddq))
    # print(manual_dynamics_mat(q, dq, ddq))

    IPython.embed()


if __name__ == '__main__':
    main()
