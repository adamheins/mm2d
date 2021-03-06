#!/usr/bin/env python
import numpy as np
import matplotlib.pyplot as plt

from mm2d.model import ThreeInputModel
from mm2d.controller import BaselineController, BaselineController2, AccelerationController
from mm2d.plotter import RealtimePlotter, ThreeInputRenderer, TrajectoryRenderer
from mm2d.trajectory import Circle, Polygon, PointToPoint, CubicTimeScaling, QuinticTimeScaling, LinearTimeScaling, CubicBezier
from mm2d.util import rms, bound_array

import IPython


# robot parameters
L1 = 1
L2 = 1
VEL_LIM = 1
ACC_LIM = 1

DT = 0.1        # timestep (s)
DURATION = 10.0  # duration of trajectory (s)

NUM_WSR = 100     # number of working set recalculations


def main():
    N = int(DURATION / DT) + 1

    model = ThreeInputModel(L1, L2, VEL_LIM, acc_lim=ACC_LIM, output_idx=[0, 1])

    W = 0.1 * np.eye(model.ni)
    Kp = np.eye(model.no)
    Kv = 0.1 * np.eye(model.no)
    controller = AccelerationController(model, W, Kp, Kv, DT, VEL_LIM, ACC_LIM)

    ts = np.array([i * DT for i in range(N)])
    qs = np.zeros((N, model.ni))
    dqs = np.zeros((N, model.ni))
    us = np.zeros((N, model.ni))
    ps = np.zeros((N, model.no))
    vs = np.zeros((N, model.no))
    pds = np.zeros((N, model.no))
    dq_cmds = np.zeros((N, model.ni))

    q0 = np.array([0, np.pi/4.0, -np.pi/4.0])
    p0 = model.forward(q0)

    # reference trajectory
    timescaling = QuinticTimeScaling(DURATION)
    trajectory = PointToPoint(p0, p0 + [1, 0], timescaling, DURATION)

    # pref, vref, aref = trajectory.sample(ts)
    # plt.figure()
    # plt.plot(ts, pref[:, 0], label='$p$')
    # plt.plot(ts, vref[:, 0], label='$v$')
    # plt.plot(ts, aref[:, 0], label='$a$')
    # plt.grid()
    # plt.legend()
    # plt.title('EE reference trajectory')
    # plt.xlabel('Time (s)')
    # plt.ylabel('Reference signal')
    # plt.show()

    q = q0
    p = p0
    dq = np.zeros(model.ni)
    qs[0, :] = q0
    ps[0, :] = p0
    pds[0, :] = p0

    robot_renderer = ThreeInputRenderer(model, q0)
    trajectory_renderer = TrajectoryRenderer(trajectory, ts)
    plotter = RealtimePlotter([robot_renderer, trajectory_renderer])
    plotter.start()

    for i in range(N - 1):

        t = ts[i]

        # controller
        pd, vd, ad = trajectory.sample(t, flatten=True)
        u = controller.solve(q, dq, pd, vd, ad)
        dq_cmd = dq + DT * u

        # step the model
        q, dq = model.step(q, dq_cmd, DT, dq_last=dq)
        p = model.forward(q)
        v = model.jacobian(q).dot(dq)

        # record
        us[i, :] = u
        dq_cmds[i, :] = dq_cmd

        dqs[i+1, :] = dq
        qs[i+1, :] = q
        ps[i+1, :] = p
        pds[i+1, :] = pd[:model.no]
        vs[i+1, :] = v

        robot_renderer.set_state(q)
        plotter.update()
    plotter.done()

    xe = pds[1:, 0] - ps[1:, 0]
    ye = pds[1:, 1] - ps[1:, 1]
    print('RMSE(x) = {}'.format(rms(xe)))
    print('RMSE(y) = {}'.format(rms(ye)))

    plt.figure()
    plt.plot(ts, pds[:, 0], label='$x_d$', color='b', linestyle='--')
    plt.plot(ts, pds[:, 1], label='$y_d$', color='r', linestyle='--')
    plt.plot(ts, ps[:, 0],  label='$x$', color='b')
    plt.plot(ts, ps[:, 1],  label='$y$', color='r')
    plt.grid()
    plt.legend()
    plt.xlabel('Time (s)')
    plt.ylabel('Position')
    plt.title('End effector position')

    plt.figure()
    plt.plot(ts, dqs[:, 0], label='$\\dot{q}_x$')
    plt.plot(ts, dqs[:, 1], label='$\\dot{q}_1$')
    plt.plot(ts, dqs[:, 2], label='$\\dot{q}_2$')
    plt.grid()
    plt.legend()
    plt.title('Joint velocity')
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity')

    plt.figure()
    plt.plot(ts, dq_cmds[:, 0], label='$\\dot{q}_x$')
    plt.plot(ts, dq_cmds[:, 1], label='$\\dot{q}_1$')
    plt.plot(ts, dq_cmds[:, 2], label='$\\dot{q}_2$')
    plt.grid()
    plt.legend()
    plt.title('Commanded Joint Velocity')
    plt.xlabel('Time (s)')
    plt.ylabel('Velocity')

    plt.figure()
    plt.plot(ts, us[:, 0], label='$u_x$')
    plt.plot(ts, us[:, 1], label='$u_1$')
    plt.plot(ts, us[:, 2], label='$u_2$')
    plt.grid()
    plt.legend()
    plt.title('Commanded joint acceleration')
    plt.xlabel('Time (s)')
    plt.ylabel('Acceleration')

    plt.figure()
    plt.plot(ts, qs[:, 0], label='$q_x$')
    plt.plot(ts, qs[:, 1], label='$q_1$')
    plt.plot(ts, qs[:, 2], label='$q_2$')
    plt.grid()
    plt.legend()
    plt.title('Joint positions')
    plt.xlabel('Time (s)')
    plt.ylabel('Joint positions')

    plt.show()


if __name__ == '__main__':
    main()
