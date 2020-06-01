import numpy as np
import util


class ThreeInputModel(object):
    def __init__(self, l1, l2, lb, ub, output_idx=[0,1,2]):
        self.ni = 3  # number of joints (inputs/DOFs)

        # control which outputs are used
        # possible outputs are: x, y, theta
        self.no = len(output_idx)
        self.output_idx = output_idx

        self.l1 = l1
        self.l2 = l2

        self.lb = lb
        self.ub = ub

    def forward(self, q):
        ''' Forward kinematic transform for the end effector. '''
        p = np.array([q[0] + self.l1*np.cos(q[1]) + self.l2*np.cos(q[1]+q[2]),
                      self.l1*np.sin(q[1]) + self.l2*np.sin(q[1]+q[2]),
                      q[1] + q[2]])
        return p[self.output_idx]

    def jacobian(self, q):
        ''' End effector Jacobian. '''
        J = np.array([
            [1, -self.l1*np.sin(q[1])-self.l2*np.sin(q[1]+q[2]), -self.l2*np.sin(q[1]+q[2])],
            [0,  self.l1*np.cos(q[1])+self.l2*np.cos(q[1]+q[2]),  self.l2*np.cos(q[1]+q[2])],
            [0, 1, 1]])
        return J[self.output_idx, :]

    def base(self, q):
        ''' Generate an array of points representing the base of the robot. '''
        x0 = q[0]
        y0 = 0
        r = 0.5
        h = 0.25

        x = np.array([x0, x0 - r, x0 - r, x0 + r, x0 + r, x0])
        y = np.array([y0, y0, y0 - h, y0 - h, y0, y0])

        return x, y

    def arm(self, q):
        ''' Generate an array of points representing the arm of the robot. '''
        x0 = q[0]
        x1 = x0 + self.l1*np.cos(q[1])
        x2 = x1 + self.l2*np.cos(q[1]+q[2])

        y0 = 0
        y1 = y0 + self.l1*np.sin(q[1])
        y2 = y1 + self.l2*np.sin(q[1]+q[2])

        x = np.array([x0, x1, x2])
        y = np.array([y0, y1, y2])

        return x, y

    def step(self, q, u, dt):
        ''' Step forward one timestep. '''
        dq = util.bound_array(u, self.lb, self.ub)
        q = q + dt * dq
        return q, dq