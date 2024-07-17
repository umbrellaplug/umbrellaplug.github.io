# -*- coding: utf-8 -*-

media_xml_start = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="{main_include}">'

media_xml_end = "\
\n    </include>\
\n</includes>"

media_xml_body = '\
\n        <include content="{cpath_type}">\
\n            <param name="content_path" value="{cpath_path}"/>\
\n            <param name="widget_header" value="{cpath_header}"/>\
\n            <param name="widget_target" value="videos"/>\
\n            <param name="list_id" value="{cpath_list_id}"/>\
\n        </include>'

history_xml_body = "\
\n        <item>\
\n            <label>$NUMBER[{spath}]</label>\
\n            <onclick>RunScript(script.umbrestuary.helper,mode=re_search)</onclick>\
\n        </item>"


stacked_media_xml_body = '\
\n        <include content="WidgetListCategoryStacked">\
\n            <param name="content_path" value="{cpath_path}"/>\
\n            <param name="widget_header" value="{cpath_header}"/>\
\n            <param name="widget_target" value="videos"/>\
\n            <param name="list_id" value="{cpath_list_id}"/>\
\n        </include>\
\n        <include content="{cpath_type}">\
\n            <param name="content_path" value="$INFO[Window(Home).Property(umbrestuary.{cpath_list_id}.path)]"/>\
\n            <param name="widget_header" value="$INFO[Window(Home).Property(umbrestuary.{cpath_list_id}.label)]"/>\
\n            <param name="widget_target" value="videos"/>\
\n            <param name="list_id" value="{cpath_list_id}1"/>\
\n        </include>'

main_menu_movies_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="MoviesMainMenu">\
\n        <item>\
\n            <label>{cpath_header}</label>\
\n            <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>\
\n            <property name="menu_id">$NUMBER[19000]</property>\
\n            <thumb>icons/sidemenu/movies.png</thumb>\
\n            <property name="id">movies</property>\
\n            <visible>!Skin.HasSetting(HomeMenuNoMovieButton)</visible>\
\n        </item>\
\n    </include>\
\n</includes>'

main_menu_tvshows_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="TVShowsMainMenu">\
\n        <item>\
\n            <label>{cpath_header}</label>\
\n            <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>\
\n            <property name="menu_id">$NUMBER[22000]</property>\
\n            <thumb>icons/sidemenu/tv.png</thumb>\
\n            <property name="id">tvshows</property>\
\n            <visible>!Skin.HasSetting(HomeMenuNoTVShowButton)</visible>\
\n        </item>\
\n    </include>\
\n</includes>'

main_menu_custom1_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="Custom1MainMenu">\
\n        <item>\
\n            <label>{cpath_header}</label>\
\n            <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>\
\n            <property name="menu_id">$NUMBER[23000]</property>\
\n            <thumb>icons/sidemenu/tv.png</thumb>\
\n            <property name="id">custom1</property>\
\n            <visible>!Skin.HasSetting(HomeMenuNoCustom1Button)</visible>\
\n        </item>\
\n    </include>\
\n</includes>'

main_menu_custom2_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="Custom2MainMenu">\
\n        <item>\
\n            <label>{cpath_header}</label>\
\n            <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>\
\n            <property name="menu_id">$NUMBER[24000]</property>\
\n            <thumb>icons/sidemenu/tv.png</thumb>\
\n            <property name="id">custom2</property>\
\n            <visible>!Skin.HasSetting(HomeMenuNoCustom2Button)</visible>\
\n        </item>\
\n    </include>\
\n</includes>'

main_menu_custom3_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="Custom3MainMenu">\
\n        <item>\
\n            <label>{cpath_header}</label>\
\n            <onclick>ActivateWindow(Videos,{main_menu_path},return)</onclick>\
\n            <property name="menu_id">$NUMBER[25000]</property>\
\n            <thumb>icons/sidemenu/tv.png</thumb>\
\n            <property name="id">custom3</property>\
\n            <visible>!Skin.HasSetting(HomeMenuNoCustom3Button)</visible>\
\n        </item>\
\n    </include>\
\n</includes>'

search_history_xml = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="SearchHistory">\
\n        <item>\
\n            <label>{spath}</label>\
\n            <onclick>RunScript(script.umbrestuary.helper,mode=re_search)</onclick>\
\n        </item>\
\n    </include>\
\n</includes>'

default_widget = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="{includes_type}">\
\n    </include>\
\n</includes>'

default_main_menu = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="{includes_type}">\
\n    </include>\
\n</includes>'

default_history = '\
<?xml version="1.0" encoding="UTF-8"?>\
\n<includes>\
\n    <include name="{includes_type}">\
\n    </include>\
\n</includes>'
