# -*- coding: utf-8 -*-
"""
Module pour l'intégration avec le framework nosetests.
"""

from funq.client import ApplicationRegistry
from funq import screenshoter
from funq.tools import which
from nose.plugins import Plugin
from ConfigParser import ConfigParser
import os, codecs, logging

LOG = logging.getLogger('nose.plugins.funq')

def message_with_sep(message):
    """retourne un message avec un séparateur."""
    sep = '-' * 70
    return (sep, message, sep)

def _patch_nose_tools_assert_functions(): # pylint: disable=C0103
    """
    patche les fonctions assert_* de nose.tools pour inclure
    des messages longs dans les message d'assertions.
    
    voir nose.tools.trivial.
    """
    from nose import tools
    import unittest
    import re
    
    caps = re.compile('([A-Z])')

    def pep8(name): # pylint: disable=C0111
        return caps.sub(lambda m: '_' + m.groups()[0].lower(), name)
    
    class Dummy(unittest.TestCase): # pylint: disable=C0111,R0904
        longMessage = True # c'est ce qui change tout.
        
        def nop(self):
            """useless"""
            pass
    dummy = Dummy('nop')
    for name in [ name for name in dir(dummy)
                if name.startswith('assert') and not '_' in name ]:
        pepd = pep8(name)
        setattr(tools, pepd, getattr(dummy, name))

def locate_funq():
    """Tente de localiser l'executable scleHooqAttach"""
    return which('funq')

# création d'un Application registry global
_APP_REGISTRY = ApplicationRegistry()

config = _APP_REGISTRY.config # pylint: disable=C0103
multi_config = _APP_REGISTRY.multi_config # pylint: disable=C0103

class FunqPlugin(Plugin):
    """
    Plugin d'integration avec nosetests.
    """
    name = 'funq'
    _current_test_name = None
    
    @staticmethod
    def current_test_name():
        return FunqPlugin._current_test_name
    
    def options(self, parser, env=None):
        env = env or os.environ
        super(FunqPlugin, self).options(parser, env=env)
        parser.add_option('--funq-conf',
                          dest='funq_conf',
                          default=env.get('NOSE_FUNQ_CONF') or 'funq.conf',
                          help="Fichier de configuration funq, defaut"
                               " `funq.conf` [NOSE_FUNQ_CONF].")
        parser.add_option('--funq-gkit',
                          dest='funq_gkit',
                          default=env.get('NOSE_FUNQ_GKIT') or 'default',
                          help="Specifie le toolkit graphique utilise."
                               " Permet de definir des alias par defaut"
                               " differents. Defaut: `default"
                               " [NOSE_FUNQ_GKIT]`")
        gkit_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'aliases-gkits.conf')
        parser.add_option('--funq-gkit-file',
                          dest='funq_gkit_file',
                          default=env.get('NOSE_FUNQ_GKIT_FILE') or gkit_file,
                          help="Specifie le fichier de description du"
                               " toolkit graphique a utiliser. Defaut:"
                               " `%s` [NOSE_FUNQ_GKIT_FILE]" % gkit_file)
        parser.add_option('--funq-attach-exe',
                          dest='funq_attach_exe',
                          default=env.get('NOSE_FUNQ_ATTACH_EXE')
                                                            or locate_funq(),
                          help="Chemin complet ver l'executable funq."
                               " [NOSE_FUNQ_ATTACH_EXE]")
        parser.add_option('--funq-trace-tests',
                          dest='funq_trace_tests',
                          default=env.get('NOSE_FUNQ_TRACE_TESTS'),
                          help="Un fichier dans lequel les traces de debut"
                               " et fin de chaque test seront ajoutees."
                               " [NOSE_FUNQ_TRACE_TESTS]")
        parser.add_option('--funq-trace-tests-encoding',
                          dest='funq_trace_tests_encoding',
                          default=env.get('NOSE_FUNQ_TRACE_TESTS_ENCODING')
                                    or 'utf-8',
                          help="encodage pour le fichier de l'option"
                               "--funq-trace-tests."
                               " [NOSE_FUNQ_TRACE_TESTS_ENCODING]")
        parser.add_option('--funq-screenshot-folder',
                          dest="funq_screenshot_folder",
                          default=env.get("NOSE_FUNQ_SCREENSHOT_FOLDER")
                                    or os.path.realpath("screenshot-errors"),
                          help="Repertoire de stockage des images en erreur."
                               " Defaut: screenshot-errors."
                               " [NOSE_FUNQ_SCREENSHOT_FOLDER]")
    
    def configure(self, options, cfg):
        Plugin.configure(self, options, cfg)
        if not self.enabled:
            return
        _patch_nose_tools_assert_functions()
        conf_file = options.funq_conf = os.path.realpath(options.funq_conf)
        if not os.path.isfile(conf_file):
            raise Exception("Fichier de conf funq manquant: `%s`" % conf_file)
        conf = ConfigParser()
        conf.read([conf_file])
        _APP_REGISTRY.register_from_conf(conf, options)
        self.trace_tests = options.funq_trace_tests
        self.trace_tests_encoding = options.funq_trace_tests_encoding
        screenshoter.init(options.funq_screenshot_folder)

    def beforeTest(self, test): # pylint: disable=C0111,C0103,R0201
        FunqPlugin._current_test_name = unicode(test.id(), 'utf-8')
        message = u"Démarrage de test `%s`" % FunqPlugin.current_test_name()
        lines = message_with_sep(message)
        for line in lines:
            LOG.info(line)
        if self.trace_tests:
            with codecs.open(self.trace_tests, 'a',
                                            self.trace_tests_encoding) as f:
                f.write('\n'.join(lines))
                f.write('\n')
            
    
    def afterTest(self, test): # pylint: disable=C0111,C0103,R0201
        message = u"Fin de test `%s`" % FunqPlugin.current_test_name()
        lines = message_with_sep(message)
        for line in lines:
            LOG.info(line)
        if self.trace_tests:
            with codecs.open(self.trace_tests, 'a',
                                            self.trace_tests_encoding) as f:
                f.write('\n'.join(lines))
                f.write('\n')
        FunqPlugin._current_test_name = None
