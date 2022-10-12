import xml.etree.ElementTree as et


if __name__ == '__main__':
    dark_xml = et.parse('./theme/jetbrains/resources/schemes/dark.xml')
    template_xml = et.parse('./tepmlates/scheme.template.xml')

    dark_options = dark_xml.findall('//attributes/option')
    template_options = template_xml.findall('//attributes/option')

    dark_eles: list[et.Element] = []
    for dark_ele in dark_options:
        if dark_ele.findall('.//option[@name="FONT_TYPE"]'):
            dark_eles.append(dark_ele)

    template_eles: list[et.Element] = []
    for template_ele in template_options:
        if template_ele.findall('.//option[@name="FONT_TYPE"]'):
            template_eles.append(template_ele)

    print(len(dark_eles))
    print(len(template_eles))

    delta_eles: list[et.Element] = []
    for dark_ele in dark_eles:
        dark_ele_name = dark_ele.attrib['name']
        if not template_xml.findall(f'./attributes/option[@name="{dark_ele_name}"]/value/option[@name="FONT_TYPE"]'):
            dark_ele.findall('./value')[0].remove(dark_ele.findall('.//option[@name="FONT_TYPE"]')[0])


    insert_parent = dark_xml.findall('./attributes')[0]
    for template_ele in template_eles:
        ele_name = template_ele.attrib['name']
        font_ele = template_ele.findall('./value/option[@name="FONT_TYPE"]')[0]
        if not dark_xml.findall(f'./attributes/option[@name="{ele_name}"]/value/option[@name="FONT_TYPE"]'):
            if dark_xml.findall(f'./attributes/option[@name="{ele_name}"]'):
                try:
                    insert_ele = dark_xml.findall(f'./attributes/option[@name="{ele_name}"]/value')[0]
                except:
                    print(ele_name)
                    raise

                et.SubElement(insert_ele, 'option', {
                    'name': 'FONT_TYPE',
                    'value': font_ele.attrib['value'],
                })
            else:
                insert_parent.append(template_ele)

    dark_xml.write('./processed.xml')
