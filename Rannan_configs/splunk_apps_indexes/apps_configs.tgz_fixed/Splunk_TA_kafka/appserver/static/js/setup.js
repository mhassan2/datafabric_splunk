$(document).ready(function() {
    $(".ManagerPageTitle").text("Splunk Add-on for Kafka");
    // 0) global vars
    // FIXME for the ebox_id, it will be different from TA to TA.
    var allSettingsEboxId = "#\\/kafka_input_setup\\/kafka_settings\\/kafka_settings\\/all_settings_id";

    var appname = Splunk.util.getCurrentApp();
    // 1) Load dependent css and javascript
    $("<link>").attr({
        rel: "stylesheet",
        type: "text/css",
        href: "/en-US/static/app/" + appname + "/css/setup.css",
    }).appendTo("head");

    // 2) Append new html
    var originFormWrapper = $(".formWrapper");
    originFormWrapper.css("display", "none");
    originFormWrapper.before(return_page());
    $("#proxySettingId").css("display", "none");
    // originFormWrapper.after(return_page());
    // originFormWrapper.remove();

    function htmlEscape(str) {
        return String(str)
                   .replace(/&/g, '&amp;')
                   .replace(/"/g, '&quot;')
                   .replace(/'/g, '&#39;')
                   .replace(/</g, '&lt;')
                   .replace(/>/g, '&gt;');
    }

    function htmlUnescape(value){
        return String(value)
                   .replace(/&quot;/g, '"')
                   .replace(/&#39;/g, "'")
                   .replace(/&lt;/g, '<')
                   .replace(/&gt;/g, '>')
                   .replace(/&amp;/g, '&');
    }

    function isTrue(value) {
        if (value === undefined) {
            return 0;
        }

        value = value.toUpperCase();
        var trues = ["1", "TRUE", "T", "Y", "YES"];
        return trues.indexOf(value) >= 0;
    }

    function updateHeaders(tableId, cols){
        var theadTr = $("#" + tableId + " .tableHead>tr");
        cols.forEach(function(col, i){
            var td = $("<td><span data-idx='" + i + "'>" + col.name+"</span></td>");
            theadTr.append(td);
        });

        var td = $("<td><span data-idx='" + cols.length + "'>Action</span></td>");
        theadTr.append(td);
        hideColumns(tableId, cols);
    };

    function setCheckBox(boxId, value) {
        if (value === undefined) {
            value = "0";
        }
        value = value.toLowerCase();
        if (value == "1" || value == "true" || value == "yes") {
            $("#" + boxId).prop("checked", true);
        } else {
            $("#" + boxId).prop("checked", false);
        }
    };

    function updateGlobalSettings(settings) {
        // Global settings
        if (settings.global_settings === undefined) {
            return;
        }

        $("#index_id").val(settings["global_settings"]["index"]);
        $("#log_level_id").val(settings["global_settings"]["log_level"]);

        // Proxy settings
        if (settings.proxy_settings === undefined) {
            return;
        }

        setCheckBox("enable_proxy_id", settings["proxy_settings"]["proxy_enabled"]);
        $("#proxy_url_id").val(settings["proxy_settings"]["proxy_url"]);
        $("#proxy_port").val(settings["proxy_settings"]["proxy_port"]);
        $("#proxy_username").val(settings["proxy_settings"]["proxy_username"]);
        $("#proxy_port").val(settings["proxy_settings"]["proxy_port"]);
        $("#proxy_type").val(settings["proxy_settings"]["proxy_type"]);

        setCheckBox("proxy_rdns_id", settings["proxy_settings"]["proxy_rdns"]);
    };

    function updateCredentialSettings(cols, credentialSettings) {
        var creds = [];
        var credsMap = {};

        if (credentialSettings) {
            for (var k in credentialSettings) {
                if (isTrue(credentialSettings[k].removed)) {
                    continue;
                }
                var rec = [k];
                for (var i = 1; i < cols.length; i++) {
                    var val = credentialSettings[k][cols[i].id]
                    if (val === undefined || val == null) {
                        val = "";
                    }
                    rec.push(val);
                }
                creds.push(rec);
                credsMap[k] = rec;
            }
        }

        return {
            "data": creds,
            "dataMap": credsMap,
        };
    };

    function hideColumns(tableId, cols) {
        for (var i = 0; i < cols.length; i++) {
            if (cols[i].hide) {
                $("#" + tableId + " td:nth-child(" + (i + 1) + "),th:nth-child(" + i + ")").hide();
            }
        }
    };

    function editRow(e) {
        currentAction = "Edit";
        var rowIdAndTableId = e.target.id.split("``");
        var table = tables[rowIdAndTableId[1]];
        var credName = $("input#" + table.columns[0].id);
        credName.prop("readonly", true);
        credName.css("background-color", "#D3D3D3");

        var did = undefined;
        for (var dialogId in dialogs) {
            if (dialogs[dialogId].table.id == table.id) {
                did = dialogId;
                break;
            }
        }

        var dialog = $("#" + did);
        dialog.text(dialog.text().replace("Add", "Edit"));
        showDialog(did);
        table.columns.forEach(function(c, i){
            $("input#" + c.id).val(table.dataMap[rowIdAndTableId[0]][i]);
        });
        return false;
    };

    function deleteRow(e) {
        var rowIdAndTableId = e.target.id.split("``");
        var table = tables[rowIdAndTableId[1]];
        for (var i = 0; i < table.data.length; i++) {
            if (table.data[i][0] == rowIdAndTableId[0]) {
                table.data.splice(i, 1);
                delete table.dataMap[rowIdAndTableId[0]];
                break;
            }
        }
        updateTable(table.id, table.data, table.columns);
        return false;
    };

    function updateTable(tableId, tableData, cols){
        if (!tableData) {
            return
        }

        var tbody = $("#" + tableId + " .tableBody");
        tbody.empty();
        tableData.forEach(function(row){
            var tr = $("<tr></tr>");
            row.forEach(function(cell){
                var td = $("<td>" + cell + "</td>");
                tr.append(td);
            });

            var id = row[0] + "``" + tableId;

            var remove_hyperlink_cell= $("<a>", {
                "href": "#",
                "id": id,
                click: deleteRow,
            }).append("Delete");

            var edit_hyperlink_cell= $("<a>", {
                "href": "#",
                "id": id,
                click: editRow,
            }).append("Edit");

            var td = $("<td>").append(remove_hyperlink_cell).append(" | ").append(edit_hyperlink_cell);
            tr.append(td);
            tbody.append(tr);
        });
        hideColumns(tableId, cols);
    };

    function showDialog(dialogId){
        $("." + dialogId).css("display", "block");
        $(".shadow").css("display", "block");
    };

    function hideDialog(dialogId){
        $("." + dialogId).css("display", "none");
        $(".shadow").css("display", "none");
    };

    function hideDialogHandler(e){
        var btnIdToDialogId = {
            "credDialogBtnCancel": "credDialog",
            "forwarderCredDialogBtnCancel": "forwarderCredDialog",
        };
        hideDialog(btnIdToDialogId[e.target.id]);
    };

    function clearFlag(){
        $("table thead td span").each(function(){
            $(this).removeClass("asque");
            $(this).removeClass("desque");
        });
    };

    function getJSONResult() {
        var result = {};
        // 1. Global Settings
        var index = $("#index_id").val();
        var log_level = $("#log_level_id").val();
        result["global_settings"] = {
            "index": index,
            "log_level": log_level,
        }

        // 2. Proxy Settings
        var proxy_settings = {
            "proxy_enabled": "0",
            "proxy_url": "",
            "proxy_port": "",
            "proxy_username": "",
            "proxy_password": "",
            "proxy_type": "",
            "proxy_rdns": "0",
        }

        var proxy_enabled = $("#enable_proxy_id")[0].checked;
        if (proxy_enabled) {
            proxy_settings["proxy_enabled"] = "1";
            proxy_settings["proxy_host"] = $("#proxy_url_id").val();
            proxy_settings["proxy_port"] = $("#proxy_port_id").val();
            proxy_settings["proxy_username"] = $("#proxy_username_id").val();
            proxy_settings["proxy_password"] = $("#proxy_password_id").val();
            proxy_settings["proxy_type"] = $("#proxy_type_id").val();
            if ($("#proxy_rdns_id")[0].checked) {
                proxy_settings["proxy_rdns"] = "1";
            }
        } else {
            proxy_settings["proxy_enabled"] = "0";
        }
        result["proxy_settings"] = proxy_settings;

        // 3. Credential Settings and Forwarder Settings
        var credSettings = {
            "credential_settings": tables.credTable,
            "forwarder_credential_settings": tables.forwarderCredTable,
        }

        for (var k in credSettings) {
            result[k] = {};
            var credTable = credSettings[k];
            for (var i = 0; i < credTable.data.length; i++){
                var temp = {};
                credTable.columns.forEach(function(c, j){
                    temp[c.id] = credTable.data[i][j];
                });
                result[k][temp[credTable.columns[0].id]] = temp;
                delete temp[credTable.columns[0].id];
            }
        }

        // return JSON.stringify(result);
        return result;
    }

    function showHideProxy() {
        if ($("#enable_proxy_id")[0].checked) {
            $(".proxy").css("display","block");
        } else {
            $(".proxy").css("display","none");
        }
    };

    function registerBtnClickHandler(did) {
        $("#" + dialogs[did].btnId).click(function(){
            currentAction = "New";
            var table = dialogs[did]["table"];
            $("input#" + table.columns[0].id).prop("readonly", false);
            table.columns.forEach(function(c, j){
                if (c.id == "index") {
                    $("input#" + c.id).val("main");
                } else {
                    $("input#" + c.id).val("");
                }
            });
            $("input#" + table.columns[0].id).css("background-color", "rgb(255, 255, 255)");
            var dialog = $("#" + did);
            var saveBtnId = did + "BtnSave";
            dialog.text(dialog.text().replace("Edit", "Add"));
            showDialog(did);
            return false;
        });
    };

    // DATA...
    // Table header
    var columns = [{
        id: "credName",
        name: "Kafka Cluster",
        name_with_desc: "Kafka Cluster",
        required: "required",
        hide: false,
        dialogHide: false,
    }, {
        id: "kafka_brokers",
        name: "Kafka Brokers",
        name_with_desc: htmlEscape("Kafka Brokers (<host:port>[,<host:port>][,...])"),
        required: "required",
        hide: false,
        dialogHide: false,
    }, {
        id: "zookeepers",
        name: "Zookeepers",
        name_with_desc: htmlEscape("Zookeepers (<host:port>[,<host:port>][,...])"),
        required: "",
        hide: true,
        dialogHide: true,
    }, {
        id: "zookeeper_chroot",
        name: "CHROOT path",
        name_with_desc: "Zookeeper CHROOT path",
        required: "",
        hide: true,
        dialogHide: true,
    }, {
        id: "kafka_topic_whitelist",
        name: "Topic Whitelist",
        name_with_desc: "Topic Whitelist. For example, my_topic.+",
        required: "",
        hide: false,
        dialogHide: false,
    }, {
        id: "kafka_topic_blacklist",
        name: "Topic Blacklist",
        name_with_desc: "Topic Blacklist. For example, _internal_topic.+",
        required: "",
        hide: false,
        dialogHide: false,
    }, {
        id: "kafka_partition",
        name: "Partition IDs",
        name_with_desc: "Partition IDs. For example, 0,1,2",
        required: "false",
        hide: false,
        dialogHide: false,
    }, {
        id: "kafka_partition_offset",
        name: "Partition Offset",
        name_with_desc: "Partition Offset",
        required: "true",
        hide: false,
        dialogHide: false,
    }, {
        id: "kafka_topic_group",
        name: "Topic Group",
        name_with_desc: "Topic Group",
        required: "false",
        hide: false,
        dialogHide: false,
    }, {
        id: "index",
        name: "Index",
        name_with_desc: "Index",
        required: "true",
        hide: false,
        dialogHide: false,
    }];

    var forwarderColumns = [{
        id: "forwarderCredName",
        name: "Forwarder Name",
        name_with_desc: "Heavy Forwarder Name",
        required: "required",
        hide: false,
        dialogHide: false,
    }, {
        id: "hostname",
        name: "Hostname/port",
        name_with_desc: "Heavy Forwarder Hostname and Port. For example, localhost:8089",
        required: "required",
        hide: false,
        dialogHide: false,
    }, {
        id: "username",
        name: "Username",
        name_with_desc: "Heavy Forwarder Username",
        required: "required",
        hide: false,
        dialogHide: false,
    }, {
        id: "password",
        name: "Password",
        name_with_desc: "Heavy Forwarder Password",
        required: "required",
        hide: true,
        dialogHide: false,
    }];

    var allSettings = $(allSettingsEboxId).val();
    allSettings = $.parseJSON(allSettings);
    updateGlobalSettings(allSettings);
    var creds = updateCredentialSettings(columns, allSettings.credential_settings);
    var forwarderCreds = updateCredentialSettings(forwarderColumns, allSettings.forwarder_credential_settings);

    var tables = {
        "credTable": {
            "id": "credTable",
            "columns": columns,
            "data": creds.data,
            "dataMap": creds.dataMap,
        },
        "forwarderCredTable": {
            "id": "forwarderCredTable",
            "columns": forwarderColumns,
            "data": forwarderCreds.data,
            "dataMap": forwarderCreds.dataMap,
        },
    };

    for (var tableId in tables) {
        updateHeaders(tableId, tables[tableId].columns);
        hideColumns(tableId, tables[tableId].columns);
        updateTable(tableId, tables[tableId].data, tables[tableId].columns);
    }

    var currentAction = "New";
    var dialogs = {
        "credDialog": {
            "id": "credDialog",
            "btnId": "btnAdd",
            "formId": "credForm",
            "table": tables.credTable,
        },
        "forwarderCredDialog": {
            "id": "forwarderCredDialog",
            "btnId": "forwarderBtnAdd",
            "formId": "forwarderCredForm",
            "table": tables.forwarderCredTable,
        },
    };

    for (var dialogId in dialogs) {
        enjectDialogForm(dialogId, dialogs[dialogId].formId, dialogs[dialogId].table.columns);
        registerBtnClickHandler(dialogId);
    }

    function enjectDialogForm(dialogId, formId, cols) {
        var form = $("#" + formId);
        cols.forEach(function(column){
            if (column.dialogHide) {
                return;
            }
            var container = $("<div></div>");
            var label = undefined;
            if (column.required == "required") {
                label = $("<label for='" + column.id + "'>" + column.name_with_desc + '<span class="requiredAsterisk"> *</span></label>');
            } else {
                label = $("<label for='" + column.id + "'>" + column.name_with_desc + "</label>");
            }
            var type = "text";
            if (column.id == "password") {
                type = "password";
            }

            // FIXME not generic code here
            var input = undefined;
            if (column.id == "kafka_partition_offset") {
                input = $("<select name='" + column.name_with_desc + "' id='" + column.id + "' " + column.required + '><option value="earliest">Earliest</option><option value="latest">Latest</option></select>');
            } else {
                input = $("<input type='" + type + "' name='" + column.name_with_desc + "' id='" + column.id + "' " + column.required + "/>");
            }
            container.append(label);
            container.append(input);
            container.append($("</br>"));
            form.append(container);
            form.append("<br><br>");
        });
        var container = $('<div style="display: inline;"></div>');
        var saveBtnId = dialogId + "BtnSave";
        var cancelBtnId = dialogId + "BtnCancel";
        container.append($("<button id='" + saveBtnId + "' type='submit'><span>Save</span></button>"));
        container.append($("<button id='" + cancelBtnId + "' <span>Cancel</span></button>"));
        form.append(container);
        $("#" + cancelBtnId).click(hideDialogHandler);
    };

    function submitHandler(event) {
        var formId = event.target.id;
        submitForm(formId);
        event.preventDefault();
    }

    function submitForm(formId) {
        var formIdToDialog = {
            "credForm": dialogs.credDialog,
            "forwarderCredForm": dialogs.forwarderCredDialog,
        }

        var dialog = formIdToDialog[formId];
        var label = $("label[for='" + dialog.table.columns[0].id + "']");

        label.text(dialog.table.columns[0].name + ": ");
        label.css("color", "black");

        var row = [];
        dialog.table.columns.forEach(function(c, i){
            row[i] = $("#" + c.id).val();
        });

        if (row[0] in dialog.table.dataMap && currentAction == "New") {
            label.text(dialog.table.columns[0].name + ": " + row[0] + " already exists");
            label.css("color", "red");
            return;
        }

        if (currentAction == "Edit") {
            for (var i = 0; i < dialog.table.data.length; i++) {
                if (dialog.table.data[i][0] == row[0]) {
                    dialog.table.data[i] = row;
                    break;
                }
            }
        } else {
            dialog.table.data.push(row);
        }
        dialog.table.dataMap[row[0]] = row;
        updateTable(dialog.table.id, dialog.table.data, dialog.table.columns);
        hideDialog(dialog.id);
        clearFlag();
    }

    setTimeout(function() {
        for (var dialogId in dialogs) {
            $("#" + dialogs[dialogId].formId).submit(submitHandler);
            $("#" + dialogs[dialogId].formId + " input").off("keypress").keypress(dialogId, function(e) {
                if (e.which == 13) {
                    $("#" + e.data + "BtnSave").click();
                    return false;
                }
            });
        }
    }, 3000);

    $("#enable_proxy_id").on("change", showHideProxy);
    showHideProxy();

    $(".splButton-primary").on("click", function(){
        var jsonResult = JSON.stringify(getJSONResult());
        $(allSettingsEboxId).val(jsonResult);
        // console.log(jsonResult);

        /*var frm = $("#eaiform");
        var payload = {
            type: frm.attr("method"),
            async: true, // FIXME
            url: frm.attr("action"),
            data: frm.serialize(),
            success: function(data) {
                data = jQuery.parseJSON(data);
                if (data["status"] == "ERROR") {
                    // FIXME to show on GUI
                    var msg = $('<li class="message info"><div style="float:left">Successfully updated "Splunk_TA_kafka". </div><div style="clear:both"></div></li>');
                    $(".MessageList").append(msg);
                    console.log("Failed");
                }
            },
            error: function(data) {
                console.log("Failed");
            }
        };
        $.ajax(payload);
        return false;*/
    });
})
