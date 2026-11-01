#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from ball_interfaces.msg import BallPos          


def normalize_angle(a):
    """把角度归一化到 [-pi, pi]"""
    while a > math.pi:
        a -= 2.0 * math.pi
    while a < -math.pi:
        a += 2.0 * math.pi
    return a


class BallNavigator(Node):
    def __init__(self):
        super().__init__('ball_navigator')

        self.targets = [
            (2.0, 3.0),   # 球1
            (5.5, 8.0),   # 球2
            (9.0, 4.0),   # 球3
        ]

        # ---- 状态 ----
        self.balls = {}          # id -> (x, y)
        self.idx = 0             # 当前要去的目标序号
        self.done = False        # 全部完成标志

        self.y = 5.54
        self.theta = 0.0

        # ---- 订阅 ----
        self.create_subscription(BallPos, 'ball_pos', self.ball_cb, 10)
        self.create_subscription(Pose, '/turtle1/pose', self.pose_cb, 10)

        # ---- 发布 ----
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)

        # ---- 10 Hz 控制循环 ----
        self.create_timer(0.1, self.control_loop)

        self.get_logger().info('ball_navigator 已启动，等待收齐 3 个球...')

    # ---------- 回调 ----------
    def ball_cb(self, msg: BallPos):
        self.balls[msg.id] = (msg.x, msg.y)
        if len(self.balls) == 3 and not hasattr(self, '_ready_logged'):
            self._ready_logged = True
            self.get_logger().info(
                f'已收齐 3 个球: {self.balls}，开始导航')

    def pose_cb(self, msg: Pose):
        self.x = msg.x
        self.y = msg.y
        self.theta = msg.theta

    # ---------- 主控制循环 ----------
    def control_loop(self):
        if self.done:
            return
        if len(self.balls) < 3:          # 没收齐不动
            return
        if self.idx >= 3:                # 全部完成
            self.stop()
            self.done = True
            self.get_logger().info('全部 3 个球已到达，任务完成！')
            return

        gx, gy = self.targets[self.idx]
        dx, dy = gx - self.x, gy - self.y
        dist = math.hypot(dx, dy)        # 到目标距离

        # 到点判定（阈值 0.3，留足余量 < 0.5 上限）
        if dist < 0.3:
            self.stop()
            self.get_logger().info(
                f'到达第 {self.idx + 1} 个球，实际坐标 '
                f'({self.x:.2f}, {self.y:.2f})，误差 {dist:.3f}')
            self.idx += 1
            return

        # 目标方位角与角度误差
        target_heading = math.atan2(dy, dx)
        err = normalize_angle(target_heading - self.theta)

        cmd = Twist()
        if abs(err) > 0.2:
            # 角度差大 → 原地转，先对准
            cmd.linear.x = 0.0
            cmd.angular.z = max(-2.0, min(2.0, 2.0 * err))
        else:
            # 对准了 → 边走边微调，越近越慢
            v = min(0.8, 1.0 * dist)
            cmd.linear.x = v
            cmd.angular.z = max(-2.0, min(2.0, 2.0 * err))
        self.cmd_pub.publish(cmd)

    def stop(self):
        self.cmd_pub.publish(Twist())    # 全 0，停下


def main():
    rclpy.init()
    node = BallNavigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
