var queryString;
var specifiedIp = "";
function getSpecifiedIp()
{
	queryString = location.search;
	if (queryString != '' && queryString != undefined )
	{
		specifiedIp = queryString.substring(queryString.indexOf("=")+1, queryString.length);
	}else{
		specifiedIp = "";
	}
}

function checkType(deviceSystem)
{
	var sys = deviceSystem.toUpperCase();
	if((sys.indexOf("MAC") != -1) || (sys.indexOf("IOS") != -1)){
		return "macbook";
	}else if (sys.indexOf("WIN") != -1){
		return "windows";
	}else if (sys.indexOf("AND") != -1){
		return "android";
	}else
		return "unknown";
}

function addBgClassByCheckIp(deviceIp)
{
	if(specifiedIp != ""){
		if(deviceIp == specifiedIp){
			return "tr-bg-selected";
		}else{
			return "";
		}
	}else{
		return "";
	}
}

var bgFlag = 0;

function addTrBg(flag)
{
	if(flag == 1){
		return "tr-bg";
	}else{
		return "";
	}
}

function generateDeviceSetting(device, index)
{
	var htmlObj = "";

	var trClass = "";
	var tmpname = "";
	
	var strMac = device.mac;
	if (strMac.length == 12)
		var mac = strMac.substring(0,2) + ":" + strMac.substring(2,4) + ":" + strMac.substring(4,6) + ":" + strMac.substring(6,8) + ":" + strMac.substring(8,10) + ":" + strMac.substring(10,12);
	else
		var mac = strMac;

  if(specifiedIp != "")
	  trClass = addBgClassByCheckIp(device.ip);
	
	if((trClass == "") && (bgFlag == 1))
	{
		trClass = "tr-bg";
	}

	if((trClass != "") && (trClass != undefined)){
		htmlObj += "<tr class='" + trClass + "'>";	
	}else{
		htmlObj += "<tr>";
	}
	
	htmlObj += "<td style=\"width:330px;\">";
	htmlObj += "<div><img src='/luci-static/resources/image/" + checkType(device.system) + ".png'/></div>";
	htmlObj += "<div>";
	htmlObj += "<label class='label-desc'>IP&#58&nbsp;</label><label class='label-content'>" + device.ip + "</label><br/>";
	htmlObj += "<label class='label-desc'>IPv6&#58&nbsp;</label><label class='label-content'>" + device.ipv6 + "</label><br/>";
	htmlObj += "<label class='label-desc'>MAC&#58&nbsp;</label><label class='label-content'>"+ mac.toUpperCase() + "</label>";
	htmlObj += "</div>";
	htmlObj += "</td>";
	htmlObj += "<td style='padding-left:200px;'>";
	htmlObj += "<label class='label-desc'>ä¸è¡&#58</label><label class='label-content'>&nbsp;"+ getNetworkRate(parseInt(device.upSpeed), 1) +"b/s</label><br/>";
	htmlObj += "<label class='label-desc'>ä¸è¡&#58</label><label class='label-content'>&nbsp;"+ getNetworkRate(parseInt(device.downSpeed), 1) +"b/s</label>";
	htmlObj += "</td>";
	htmlObj += "</tr>";
	$("tbody").append(htmlObj);
	if(bgFlag == 0){
		bgFlag = 1;
	}else{
		bgFlag = 0;
	}
}

function confirmPC_Blacklist(blackip)
{
    cleanPopWindowContentFromIframe();
				
    //å¡«ååå®¹
	$("#pop_window_title", window.parent.document).html("ç¡®è®¤æé»");
	$("#pop_window_icon", window.parent.document).html('<div class="pop_window_icon_alert"></div>');
	if (lanip.indexOf(blackip) != -1)
		$("#pop_window_message", window.parent.document).html("æ¨ç¡®è®¤å°å½åè®¾å¤ä»ç½å³ä¸­æé»ï¼å¦ææ§è¡è¯¥æä½ï¼æ¬è®¾å¤å°æ æ³è®¿é®ç½å³åè±ç¹ç½ï¼æ¨å¿é¡»éè¿å¦å¤ä¸å°è®¾å¤è¿æ¥æ¬ç½å³æè½éæ°å°è¯¥è®¾å¤ä»é»ååä¸­æ¾åã");
	else
	  $("#pop_window_message", window.parent.document).html("æ¨æ­£å¨è¿è¡æé»æä½ï¼è¯¥è®¾å¤æé»åå°ä»å½ååè¡¨ä¸­ç´æ¥å é¤ï¼æ¨å¯è¿å¥è®¾å¤é»ååä¸­æ¾åå®ã");
			
	//æ´æ¹ç¡®è®¤æä½å½æ°
	var eid = parent.document.getElementById("confirm");
	if ( isIE7Browser() )
	{
		eid.onclick = function() { set_host_black() };
	}
	else
	{
		eid.setAttribute("onclick","document.getElementById('device_iframe').contentWindow.set_host_black()");
	}
	showOrHidePopWindowFromIframe("show");
}

function cancelBlacklist()
{
	cleanPopWindowContentFromIframe();
				
	//å¡«ååå®¹
	$("#pop_window_title", window.parent.document).html("ç¡®è®¤æ¤éæé»");
	$("#pop_window_icon", window.parent.document).html('<div class="pop_window_icon_alert"></div>');
	$("#pop_window_message", window.parent.document).html("æ¨æ­£å¨è¿è¡æ¤éæé»æä½ï¼è¯¥è®¾å¤æ¤éæé»åå°ä»è®¾å¤é»ååä¸­ç´æ¥å é¤ï¼æ¨å¯å¨ç»ç«¯åè¡¨ä¸­æ¾åå®ã");
			
	//æ´æ¹ç¡®è®¤æä½å½æ°
	var eid = parent.document.getElementById("confirm");
	if ( isIE7Browser() )
	{
		eid.onclick = function() { removeBlack() };
	}
	else
	{
		eid.setAttribute("onclick","document.getElementById('device_iframe').contentWindow.removeBlack()");
	}
	showOrHidePopWindowFromIframe("show");
}

function displayblackhosts(device)
{
	var htmlObj = "";
	var trClass = "";
	

	
	var strMac = device.mac;
	if (strMac.length == 12)
		var mac = strMac.substring(0,2) + ":" + strMac.substring(2,4) + ":" + strMac.substring(4,6) + ":" + strMac.substring(6,8) + ":" + strMac.substring(8,10) + ":" + strMac.substring(10,12);
	else
		var mac = strMac;
		
	if(bgFlag == 1)
		trClass = "tr-bg";		

	if((trClass != "") && (trClass != undefined)){
		htmlObj += "<tr class='" + trClass + "'>";	
	}else{
		htmlObj += "<tr>";
	}

	var tmp = "";
	if (device.ipv6 != undefined)
		tmp = device.ipv6;	
	
	htmlObj += "<td>";
	htmlObj += "<div><img src='/luci-static/resources/image/" + checkType(device.system) + ".png'/></div>";
	htmlObj += "<div>";
	htmlObj += "<label class='label-desc'>IP&#58&nbsp;</label><label class='label-content'>" + device.ip + "</label><br/>";
	htmlObj += "<label class='label-desc'>IPv6&#58&nbsp;</label><label class='label-content'>" + tmp + "</label><br/>";
	htmlObj += "<label class='label-desc'>MAC&#58&nbsp;</label><label class='label-content blackmac'>"+ mac.toUpperCase() + "</label>";
	htmlObj += "</div>";
	htmlObj += "</td>";
    htmlObj += "<td></td><td></td>"; 
	htmlObj += '<td class="restriction-td">';
 	htmlObj += "<span class='switch-button'><a style='color:#39BA93'>æ¤éæé»<a/> </span>";
	htmlObj += "</td>";
	htmlObj += "</tr>";
	
	$("tbody").append(htmlObj);
	if(bgFlag == 0){
		bgFlag = 1;
	}else{
		bgFlag = 0;
	}	
}