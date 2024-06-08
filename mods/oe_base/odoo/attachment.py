# -*- coding: utf-8 -*-

from odoo.tools import human_size
from odoo.fields import Binary, Field
import logging
_logger = logging.getLogger(__name__)
_logger.info('Initializing bin_size_efficiency module ...')


# Replace Binary.compute_value introduced in v13.0
if Binary.compute_value != Field.compute_value:
    Binary.compute_value = Field.compute_value


def ir_attachment_compute_datas_new(self):
    if not self._context.get('bin_size'):
        return ir_attachment_compute_datas_orig(self)

    for attach in self:
        attach.datas = human_size(attach.file_size)


def image_write_new(self, records, value):
    ctx = records.env.context
    if ctx.get('bin_size') or ctx.get('bin_size_' + self.name):
        super(Image, self).write(records, value)
    else:
        image_write_orig(self, records, value)


try:
    from odoo.addons.base.models.ir_attachment import IrAttachment
except ImportError:
    from odoo.addons.base.ir.ir_attachment import IrAttachment

ir_attachment_compute_datas_orig = IrAttachment._compute_datas
IrAttachment._compute_datas = ir_attachment_compute_datas_new


try:
    from odoo.fields import Image

    image_write_orig = Image.write
    Image.write = image_write_new

except ImportError:
    pass
