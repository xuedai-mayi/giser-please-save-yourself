'''
16240110 杜昊 2026.3.19

为了方便的直接对矢量数据进行操作和直观的比较压缩前后的数据变化情况，
本程序使用arcpy,
在Arcgis Pro中内置的notebook中实现

'''
# -*- coding: utf-8 -*-

import arcpy
import math

arcpy.env.overwriteOutput = True


def point_to_segment_distance(p, a, b):
    """计算点 p 到线段 ab 的最短距离"""
    px, py = p
    ax, ay = a
    bx, by = b

    dx = bx - ax
    dy = by - ay

    # 如果线段退化成一个点
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)

    # 计算投影参数 t
    t = ((px - ax) * dx + (py - ay) * dy) / float(dx * dx + dy * dy)

    if t < 0:
        nx, ny = ax, ay
    elif t > 1:
        nx, ny = bx, by
    else:
        nx = ax + t * dx
        ny = ay + t * dy

    return math.hypot(px - nx, py - ny)


def douglas_peucker(points, tolerance):
    """Douglas-Peucker 线简化"""
    if len(points) <= 2:
        return points[:]

    start = points[0]
    end = points[-1]

    max_dist = -1.0
    max_index = -1

    for i in range(1, len(points) - 1):
        d = point_to_segment_distance(points[i], start, end)
        if d > max_dist:
            max_dist = d
            max_index = i

    if max_dist > tolerance:
        left = douglas_peucker(points[:max_index + 1], tolerance)
        right = douglas_peucker(points[max_index:], tolerance)
        return left[:-1] + right
    else:
        return [start, end]


def simplify_ring(ring_points, tolerance):
    """对单个闭合环进行简化"""
    # 闭合环至少 4 个点：A-B-C-A
    if len(ring_points) < 4:
        return ring_points

    # 去掉最后一个重复点，转成开放折线
    open_ring = ring_points[:-1]

    if len(open_ring) < 3:
        return ring_points

    simplified = douglas_peucker(open_ring, tolerance)

    # 去重但保持顺序
    unique_pts = []
    for pt in simplified:
        if pt not in unique_pts:
            unique_pts.append(pt)

    # 至少保留 3 个不同点
    if len(unique_pts) < 3:
        unique_pts = []
        for pt in open_ring:
            if pt not in unique_pts:
                unique_pts.append(pt)
            if len(unique_pts) == 3:
                break

    # 重新闭合
    if unique_pts[0] != unique_pts[-1]:
        unique_pts.append(unique_pts[0])

    return unique_pts


def simplify_single_polygon(input_fc, output_fc, tolerance):
    desc = arcpy.Describe(input_fc)
    spatial_ref = desc.spatialReference

    if desc.shapeType.upper() != "POLYGON":
        raise ValueError("输入必须是 Polygon 面要素。")

    # 先复制，保留属性表
    if arcpy.Exists(output_fc):
        arcpy.Delete_management(output_fc)
    arcpy.CopyFeatures_management(input_fc, output_fc)

    # 因为该处理对象只有一个面，所以只更新第一条
    with arcpy.da.UpdateCursor(output_fc, ["SHAPE@"]) as cursor:
        for row in cursor:
            geom = row[0]

            if geom is None:
                continue

            # 取第一个 part 的所有点
            part = geom.getPart(0)

            ring_points = []
            for p in part:
                if p is not None:
                    ring_points.append((p.X, p.Y))

            if len(ring_points) < 3:
                continue

            # 如果没闭合，手动闭合
            if ring_points[0] != ring_points[-1]:
                ring_points.append(ring_points[0])

            # 原始点数（去掉闭合重复点后统计）
            original_point_count = len(ring_points) - 1

            # 简化外环
            simplified_ring = simplify_ring(ring_points, tolerance)

            if len(simplified_ring) < 4:
                continue

            # 简化后点数（去掉闭合重复点后统计）
            simplified_point_count = len(simplified_ring) - 1

            # 计算压缩率
            if original_point_count > 0:
                compression_rate = (
                    (original_point_count - simplified_point_count) / float(original_point_count)
                ) * 100.0
            else:
                compression_rate = 0.0

            # 重建 Polygon
            arr = arcpy.Array([arcpy.Point(x, y) for x, y in simplified_ring])
            new_geom = arcpy.Polygon(arr, spatial_ref)

            row[0] = new_geom
            cursor.updateRow(row)

            print("原始点数: {}".format(original_point_count))
            print("简化后点数: {}".format(simplified_point_count))
            print("压缩率: {:.2f}%".format(compression_rate))
            print("单一面要素概化完成：{}".format(output_fc))

            break


# =========================
# 参数区
# =========================
input_fc = r"C:\Users\32290\Desktop\importent\日常实验\算法\数据压缩\3.空间数据压缩上机课\江苏省\江苏省.shp"
output_fc = r"C:\Users\32290\Desktop\importent\日常实验\算法\数据压缩\3.空间数据压缩上机课\江苏省\江苏省_简化.shp"
tolerance = 3000.0

simplify_single_polygon(input_fc, output_fc, tolerance)


