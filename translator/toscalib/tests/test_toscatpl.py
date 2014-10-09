#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os

from translator.toscalib.elements.nodetype import NodeType
from translator.toscalib.functions import GetInput
from translator.toscalib.functions import GetProperty
from translator.toscalib.tests.base import TestCase
from translator.toscalib.tosca_template import ToscaTemplate


class ToscaTemplateTest(TestCase):

    '''TOSCA template.'''
    tosca_tpl = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data/tosca_single_instance_wordpress.yaml")
    tosca = ToscaTemplate(tosca_tpl)

    tosca_elk_tpl = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data/tosca_elk.yaml")

    def test_version(self):
        self.assertEqual(self.tosca.version, "tosca_simple_1.0")

    def test_description(self):
        expected_description = "TOSCA simple profile with wordpress, " \
                               "web server and mysql on the same server."
        self.assertEqual(self.tosca.description, expected_description)

    def test_inputs(self):
        self.assertEqual(
            ['cpus', 'db_name', 'db_port',
             'db_pwd', 'db_root_pwd', 'db_user'],
            sorted([input.name for input in self.tosca.inputs]))

        input_name = "db_port"
        expected_description = "Port for the MySQL database."
        for input in self.tosca.inputs:
            if input.name == input_name:
                self.assertEqual(input.description, expected_description)

    def test_node_tpls(self):
        '''Test nodetemplate names.'''
        self.assertEqual(
            ['mysql_database', 'mysql_dbms', 'server',
             'webserver', 'wordpress'],
            sorted([tpl.name for tpl in self.tosca.nodetemplates]))

        tpl_name = "mysql_database"
        expected_type = "tosca.nodes.Database"
        expected_properties = ['db_name', 'db_password', 'db_user']
        expected_capabilities = ['database_endpoint']
        expected_requirements = [{'host': 'mysql_dbms'}]
        expected_relationshp = ['tosca.relationships.HostedOn']
        expected_host = ['mysql_dbms']
        expected_interface = ['tosca.interfaces.node.Lifecycle']

        for tpl in self.tosca.nodetemplates:
            if tpl_name == tpl.name:
                '''Test node type.'''
                self.assertEqual(tpl.type, expected_type)

                '''Test properties.'''
                self.assertEqual(
                    expected_properties,
                    sorted([p.name for p in tpl.properties]))

                '''Test capabilities.'''
                self.assertEqual(
                    expected_capabilities,
                    sorted([p.name for p in tpl.capabilities]))

                '''Test requirements.'''
                self.assertEqual(
                    expected_requirements, tpl.requirements)

                '''Test relationship.'''
                self.assertEqual(
                    expected_relationshp,
                    [x.type for x in tpl.relationship.keys()])
                self.assertEqual(
                    expected_host,
                    [y.name for y in tpl.relationship.values()])

                '''Test interfaces.'''
                self.assertEqual(
                    expected_interface,
                    [x.type for x in tpl.interfaces])

            '''Test property value'''
            if tpl.name == 'server':
                for property in tpl.properties:
                    if property.name == 'os_type':
                        self.assertEqual(property.value, 'Linux')

    def test_outputs(self):
        self.assertEqual(
            ['website_url'],
            sorted([output.name for output in self.tosca.outputs]))

    def test_interfaces(self):
        wordpress_node = [
            node for node in self.tosca.nodetemplates
            if node.name == 'wordpress'][0]
        interfaces = wordpress_node.interfaces
        self.assertEqual(2, len(interfaces))
        for interface in interfaces:
            if interface.name == 'create':
                self.assertEqual('tosca.interfaces.node.Lifecycle',
                                 interface.type)
                self.assertEqual('wordpress_install.sh',
                                 interface.implementation)
                self.assertIsNone(interface.input)
            elif interface.name == 'configure':
                self.assertEqual('tosca.interfaces.node.Lifecycle',
                                 interface.type)
                self.assertEqual('wordpress_configure.sh',
                                 interface.implementation)
                self.assertEqual(4, len(interface.input))
                wp_db_port = interface.input['wp_db_port']
                self.assertTrue(isinstance(wp_db_port, GetProperty))
                self.assertEqual('get_property', wp_db_port.name)
                self.assertEqual(['SELF',
                                  'database_endpoint',
                                  'port'],
                                 wp_db_port.args)
                result = wp_db_port.result()
                self.assertTrue(isinstance(result, GetInput))
            else:
                raise AssertionError(
                    'Unexpected interface: {0}'.format(interface.name))

    def test_normative_type_by_short_name(self):
        #test template with a short name Compute
        template = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "data/test_tosca_normative_type_by_shortname.yaml")

        tosca_tpl = ToscaTemplate(template)
        expected_type = "tosca.nodes.Compute"
        for tpl in tosca_tpl.nodetemplates:
            self.assertEqual(tpl.type, expected_type)
        for tpl in tosca_tpl.nodetemplates:
            compute_type = NodeType(tpl.type)
            self.assertEqual(
                ['tosca.capabilities.Container'],
                [c.type for c in compute_type.capabilities])

    def test_template_with_no_inputs(self):
        tosca_tpl = self._load_template('test_no_inputs_in_template.yaml')
        self.assertEqual(0, len(tosca_tpl.inputs))

    def test_template_with_no_outputs(self):
        tosca_tpl = self._load_template('test_no_outputs_in_template.yaml')
        self.assertEqual(0, len(tosca_tpl.outputs))

    def test_relationship_interface(self):
        template = ToscaTemplate(self.tosca_elk_tpl)
        for node_tpl in template.nodetemplates:
            if node_tpl.name == 'nodejs':
                config_interface = 'tosca.interfaces.relationship.Configure'
                relation = node_tpl.relationship
                for key in relation.keys():
                    rel_tpl = relation.get(key).get_relationship_template()
                    interfaces = rel_tpl[0].interfaces
                    for interface in interfaces:
                        self.assertEqual(config_interface,
                                         interface.type)
                        self.assertEqual('pre_configure_source',
                                         interface.name)
                        self.assertEqual('nodejs/pre_configure_source.sh',
                                         interface.implementation)

    def test_template_macro(self):
        template = ToscaTemplate(self.tosca_elk_tpl)
        for node_tpl in template.nodetemplates:
            if node_tpl.name == 'mongo_server':
                self.assertEqual(
                    ['disk_size', 'mem_size', 'num_cpus', 'os_arch',
                     'os_distribution', 'os_type', 'os_version'],
                    sorted([p.name for p in node_tpl.properties]))
