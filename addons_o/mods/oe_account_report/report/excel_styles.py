#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import xlwt

# Title
subTitle_style = xlwt.easyxf(strg_to_parse='font: name Arial, bold on; align: wrap on, vert centre, horiz centre;')
subTitle_style_color = xlwt.easyxf(strg_to_parse='font: name Arial, bold on, height 200; align: wrap on, vert centre, horiz centre; \
                                    borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
subTitle_style_color_left = xlwt.easyxf('font: height 200, bold on; align: wrap on, vert centre, horiz left; \
                                    borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
subTitle_style_color_right = xlwt.easyxf('font: height 200, bold on; align: wrap on, vert centre, horiz right; \
                                    borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')

# Text Body
normal_style_text = xlwt.easyxf('font: name Arial, height 180; align: wrap on, vert centre, horiz centre;')
normal_style_left = xlwt.easyxf('font: name Arial, bold off, height 180; align: wrap on, vert bottom, horiz left;')
normal_style_right = xlwt.easyxf('font: name Arial, bold off, height 180; align: wrap on, vert bottom, horiz right;')
normal_style_text_left_sub = xlwt.easyxf('font: name Arial, height 170; align: wrap on, vert centre, horiz left;')
normal_style_left_date = xlwt.easyxf('font: name Arial, bold off, height 180; align: wrap on, vert bottom, horiz left;')
normal_style_num = xlwt.easyxf('font: name Arial,bold on, italic off, height 180; align: horiz right;', num_format_str='###,###,##0.00')
normal_style_num_total = xlwt.easyxf('font: name Arial, bold on, italic off, height 180; align: horiz right;', num_format_str='###,###,##0.00')

# Text Border
normal_style_left_bottom = xlwt.easyxf('font: name Arial, bold off, height 180; align: wrap on, vert bottom, horiz left;\
                                 borders: left no_line, right no_line, top no_line, bottom thick;')
