import cadquery

size = 50

box=cadquery.Workplane('top').box(size,size,size)

show_object(box)