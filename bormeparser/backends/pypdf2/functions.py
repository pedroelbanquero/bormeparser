#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from PyPDF2 import PdfFileReader
from collections import OrderedDict

from bormeparser.regex import regex_cargos, regex_empresa, regex_argcolon, regex_noarg, is_acto_cargo, REGEX_ARGCOLON, REGEX_NOARG, REGEX_TEXT, REGEX_BORME_NUM, REGEX_BORME_CVE

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)
logger.setLevel(logging.WARN)

DATA = OrderedDict()
for key in ('borme_fecha', 'borme_num', 'borme_seccion', 'borme_subseccion', 'borme_provincia', 'borme_cve'):
    DATA[key] = None


def clean_data(data):
    return data.replace('\(', '(').replace('\)', ')').replace('  ', ' ').strip()


def parse_file(filename):
    cabecera = False
    texto = False
    data = ""
    actos = {}
    nombreacto = None
    anuncio_id = None
    empresa = None
    fecha = False
    numero = False
    seccion = False
    subseccion = False
    provincia = False
    cve = False

    reader = PdfFileReader(open(filename, 'rb'))
    for n in range(0, reader.getNumPages()):
        content = reader.getPage(n).getContents().getData()
        logger.debug('---- BEGIN OF PAGE ----')
        
        # Python 3
        if isinstance(content, bytes):
            content = content.decode('unicode_escape')
        #logger.debug(content)

        for line in content.split('\n'):
            logger.debug('### LINE: %s' % line)
            if line.startswith('/Cabecera_acto'):
                logger.debug('START: cabecera')
                cabecera = True
                data = ""
                actos = {}
                continue

            if line.startswith('/Texto_acto'):
                logger.debug('START: texto')
                logger.debug('  nombreacto: %s' % nombreacto)
                logger.debug('  data: %s' % data)
                texto = True
                continue

            if line.startswith('/Fecha'):
                if not DATA['borme_fecha']:
                    logger.debug('START: fecha')
                    fecha = True
                continue

            if line.startswith('/Numero_BORME'):
                if not DATA['borme_num']:
                    logger.debug('START: numero')
                    numero = True
                continue

            if line.startswith('/Seccion'):
                if not DATA['borme_seccion']:
                    logger.debug('START: seccion')
                    seccion = True
                continue

            if line.startswith('/Subseccion'):
                if not DATA['borme_subseccion']:
                    logger.debug('START: subseccion')
                    subseccion = True
                continue

            if line.startswith('/Provincia'):
                if not DATA['borme_provincia']:
                    logger.debug('START: provincia')
                    provincia = True
                continue

            if line.startswith('/Codigo_verificacion'):
                if not DATA['borme_cve']:
                    logger.debug('START: cve')
                    cve = True
                continue

            if line == 'BT':
                # Begin text object
                continue

            if line == 'ET':
                # End text object
                if cabecera:
                    logger.debug('END: cabecera')
                    cabecera = False
                    data = clean_data(data)
                    anuncio_id, empresa = regex_empresa(data)
                    logger.debug('  anuncio_id: %s' % anuncio_id)
                    logger.debug('  empresa: %s' % empresa)
                    data = ""
                if texto:
                    logger.debug('END: texto')
                    texto = False
                    logger.debug('  nombreacto: %s' % nombreacto)
                    logger.debug('  data: %s' % data)

                    if nombreacto:
                        data = clean_data(data)
                        actos[nombreacto] = data
                        logger.debug('  nombreacto: %s' % nombreacto)
                        logger.debug('  data: %s' % data)
                        DATA[anuncio_id] = {'Empresa': empresa, 'Actos': actos}
                        nombreacto = None
                        data = ""
                continue

            if not any([texto, cabecera, fecha, numero, seccion, subseccion, provincia, cve]):
                continue

            if line == '/F1 8 Tf':
                # Font 1: bold
                if nombreacto:
                    logger.debug('  nombreacto: %s' % nombreacto)
                    data = clean_data(data)
                    logger.debug('  data_3: %s' % data)
                    if is_acto_cargo(nombreacto):
                        data = regex_cargos(data)
                        logger.debug('  data_4: %s' % data)
                    actos[nombreacto] = data
                    data = ""
                    nombreacto = None
                logger.debug('START: font bold')
                continue

            if line == '/F2 8 Tf':
                # Font 2: normal
                nombreacto = clean_data(data)[:-1]

                while True:
                    end = True

                    if REGEX_ARGCOLON.match(nombreacto):
                        end = False
                        acto_colon, arg_colon, nombreacto = regex_argcolon(nombreacto)
                        if acto_colon == 'Fe de erratas':  # FIXME: check
                            actos[acto_colon] = arg_colon
                        else:
                            actos[acto_colon] = {'Socio Único': {arg_colon}}

                        logger.debug('  nombreacto2: %s -- %s' % (acto_colon, arg_colon))
                        logger.debug('  data: %s' % data)

                    elif REGEX_NOARG.match(nombreacto):
                        end = False
                        acto_noarg, nombreacto = regex_noarg(nombreacto)
                        actos[acto_noarg] = True
                        logger.debug('  acto_noarg: %s' % acto_noarg)
                        logger.debug('  data: %s' % data)

                    if end:
                        break

                logger.debug('  nombreacto2: %s' % nombreacto)
                logger.debug('  data: %s' % data)
                data = ""
                logger.debug('  data_1: %s' % data)
                logger.debug('START: font normal')
                continue

            m = REGEX_TEXT.match(line)
            if m:
                if fecha:
                    DATA['borme_fecha'] = m.group(1)
                    fecha = False
                    logger.debug('fecha: %s' % DATA['borme_fecha'])
                if numero:
                    text = m.group(1)
                    DATA['borme_num'] = int(REGEX_BORME_NUM.match(text).group(1))
                    numero = False
                    logger.debug('num: %d' % DATA['borme_num'])
                if seccion:
                    DATA['borme_seccion'] = m.group(1)
                    seccion = False
                    logger.debug('seccion: %s' % DATA['borme_seccion'])
                if subseccion:
                    DATA['borme_subseccion'] = m.group(1)
                    subseccion = False
                    logger.debug('subseccion: %s' % DATA['borme_subseccion'])
                if provincia:
                    DATA['borme_provincia'] = m.group(1)
                    provincia = False
                    logger.debug('provincia: %s' % DATA['borme_provincia'])
                if cve:
                    text = m.group(1)
                    DATA['borme_cve'] = REGEX_BORME_CVE.match(text).group(1)
                    cve = False
                    logger.debug('cve: %s' % DATA['borme_cve'])
                #logger.debug(m.group(1))
                data += ' ' + m.group(1)
                #logger.debug('MORE DATA')
                logger.debug('TOTAL DATA: %s' % data)

        logger.debug('---- END OF PAGE ----')

    return DATA