import cadquery

width = 50

box=cadquery.Workplane('top').box(width,width,width)

show_object(box)