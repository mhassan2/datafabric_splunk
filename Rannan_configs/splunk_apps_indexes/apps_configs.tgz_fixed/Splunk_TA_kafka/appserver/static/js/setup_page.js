function return_page() {
    return '<div class="formWrapper">\
                <div class="fieldsetWrapper" id="globalSettingId">\
                    <fieldset>\
                        <legend>Global Settings</legend>\
                        <div class="widget" style="display:none" >\
                            <label>Index</label>\
                            <div>\
                                <input id="index_id" type="text" value="main" class="index_input">\
                                <div class="widgeterror"></div>\
                            </div>\
                        </div>\
                        <div class="widget">\
                            <label>Logging level</label>\
                            <div>\
                                <select id="log_level_id">\
                                    <option selected="selected" value="INFO">INFO</option>\
                                    <option value="DEBUG">DEBUG</option>\
                                    <option value="ERROR">ERROR</option>\
                                </select>\
                                <div class="widgeterror"></div>\
                            </div>\
                        </div>\
                    </fieldset>\
                </div>\
                <div class="fieldsetWrapper" id="proxySettingId">\
                    <fieldset>\
                        <legend>Proxy Settings</legend>\
                        <div class="checkboxWidget widget">\
                            <div>\
                                <div class="widgeterror"></div>\
                                <div>\
                                    <input type="checkbox" name="enable_proxy" id="enable_proxy_id">\
                                    <span style="display:inline-block">Enable Proxy</span>\
                                </div>\
                            </div>\
                        </div>\
                        <div class="widget" style="display: block;">\
                            <div class="proxy">\
                                <div class="widget" style="display: block;">\
                                    <label>Proxy host</label>\
                                    <div>\
                                        <input class="index_input" type="text" id="proxy_url_id">\
                                    </div>\
                                    <div class="widgeterror"></div>\
                                </div>\
                                <div class="widget" style="display: block;">\
                                    <label>Proxy port</label>\
                                    <div>\
                                        <input class="index_input" type="text" id="proxy_port_id">\
                                    </div>\
                                    <div class="widgeterror"></div>\
                                </div>\
                                <div class="widget" style="display: block;">\
                                    <label>Proxy username</label>\
                                    <div>\
                                        <input class="index_input" type="text" id="proxy_username_id">\
                                    </div>\
                                    <div class="widgeterror"></div>\
                                </div>\
                                <div class="widget" style="display: block;">\
                                    <label>Proxy password</label>\
                                    <div>\
                                        <input class="index_input" type="password" id="proxy_password_id">\
                                    </div>\
                                    <div class="widgeterror"></div>\
                                </div>\
                                <div class="widget" style="display: block;">\
                                    <label>Proxy type</label>\
                                    <div>\
                                        <select id="proxy_type_id">\
                                            <option selected="selected" value="http">http</option>\
                                            <option value="http_no_tunnel">http_no_tunnel</option>\
                                            <option value="socks4">socks4</option>\
                                            <option value="socks5">socks5</option>\
                                        </select>\
                                        <div class="widgeterror"></div>\
                                    </div>\
                                </div>\
                                <div class="widget" style="display: block;">\
                                    <div>\
                                        <input type="checkbox" name="proxy_rdns" id="proxy_rdns_id">\
                                        <span style="display:inline-block">Use Proxy to do DNS resolution</span>\
                                    </div>\
                                    <div class="widgeterror"></div>\
                                </div>\
                            </div>\
                        </div> <!--end of proxy div-->\
                    </fieldset>\
                </div>\
                <div class="fieldsetWrapper" id="credSettingId">\
                    <fieldset>\
                        <legend>Credential Settings</legend>\
                        <div>\
                            <span class="float-left" style="font-size:14px;">Kafka Cluster</span>\
                            <button id="btnAdd" type="submit" class="float-right credBtn"><span>Add Kafka Cluster</span></button>\
                        </div>\
                        <br>\
                        <br>\
                        <div>\
                            <table id="credTable" class="table mg-10" style="display: table;">\
                                <thead class="tableHead">\
                                    <tr>\
                                    </tr>\
                                </thead>\
                                <tbody class="tableBody">\
                                </tbody>\
                            </table>\
                        </div>\
                        <div>\
                            <span class="float-left" style="font-size:14px;">Forwarders</span>\
                            <button id="forwarderBtnAdd" type="submit" class="float-right credBtn"><span>Add Forwarder</span></button>\
                        </div>\
                        <br>\
                        <br>\
                        <div>\
                            <table id="forwarderCredTable" class="table mg-10" style="display: table;">\
                                <thead class="tableHead">\
                                    <tr>\
                                    </tr>\
                                </thead>\
                                <tbody class="tableBody">\
                                </tbody>\
                            </table>\
                        </div>\
                    </fieldset>\
                </div>\
                <div class="shadow">\
                </div>\
            </div> <!-- end of form_wrapper-->\
            <div class="dialog credDialog">\
                <div id="credDialog" class="dialog-header color-gray pd-16">\
                    Add Kafka Cluster\
                </div>\
                <div class="dialog-content pd-16">\
                    <form autocomplete="off" id="credForm" class="credform">\
                    </form>\
                </div>\
            </div>\
            <div class="dialog2 forwarderCredDialog">\
                <div id="forwarderCredDialog" class="dialog-header color-gray pd-16">\
                    Add Heavy Forwarder\
                </div>\
                <div class="dialog-content pd-16">\
                    <form autocomplete="off" id="forwarderCredForm" class="credform">\
                    </form>\
                </div>\
            </div>\
        </div>';
}

function return_cred_form() {
        return '<div class="dialog">\
            <div class="dialog-header pd-16">\
                Add New Credentials\
            </div>\
            <div class="dialog-content pd-16">\
                <form autocomplete="off" id="form">\
                </form>\
            </div>\
        </div>';
}
