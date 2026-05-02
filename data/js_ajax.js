// TODO: create a generic ajax panel/lightbox to show status/results info
//all: https://gist.github.com/addyosmani/1184226
//http://starter.pixelgraphics.us/
//https://gasparesganga.com/labs/jquery-loading-overlay
//https://labs.danielcardoso.net/load-awesome/

(function($) {

	if (!$.SWLjs) {
		$.SWLjs = {}
	}

	$.SWLjs.messageHandler = function(message, options) {
		if (jQuery('#notification').length && (options.type == "message" || options.type == "error")) {
			showSitePageNotification(options.type, message);
		}
		else
		{
			alert(message);
		}
	};

	$.SWLjs.ajax = function(ajaxData, options, el) {

		// To avoid scope issues, use 'base' instead of 'this'
		// to reference this class from internal events and functions.
		var base = this;

		//TODO: FORM

		// Access to jQuery and DOM versions of element
		if (arguments.length == 2)
		{
			el = document.body;
		}
		else
		{
			el = (typeof el === "undefined") ? document.body : el;
		}

		base.el = el;
		base.$el = $(el);

		// Add a reverse reference to the DOM object
		if (typeof base.$el.data("SWLjs.ajax") !== "undefined")
		{
			base = base.$el.data("SWLjs.ajax");
		}
		else
		{
			base.$el.data("SWLjs.ajax", base);
		}

		base.buildLoading = function()
		{
			// Assumes init has been called
			if (base.options.loadingIconEnabled)
			{
				// TODO: Add support for displaying icon in relation to the element that called the ajax vs just middle of the screen.
				if (!base.loadingIcon)
				{
					base.loadingIcon = $('<span style="display: none;" id="swl_ajax_loader" class="fa-solid fa-spinner fa-spin-pulse fa-2x swl_ajax_loader"></span>');
				}

				base.$el.append(base.loadingIcon);
			}

			if (base.options.loadingOverlayEnabled && typeof $.LoadingOverlay !== 'undefined') {
				base.setupOverlayOptions();
				base.setupOverlayContainer();
			}
		};

		base.setupOverlayOptions = function() {
			let options = {};

			if (base.options.loadingOverlayEnabled === true) {
				base.options.loadingOverlayEnabled = {};
			} else {
				options = base.options.loadingOverlayEnabled
			}

			options.background = options?.background || 'rgba(255, 255, 255, .6)';
			options.image = ''; // image needs to be set to empty string when using 'custom' option
			options.custom = buildOverlayIcon();

			base.options.loadingOverlayEnabled = options;
		}

		base.setupOverlayContainer = function() {
			const { containerID } = base.options.loadingOverlayEnabled || {};

			if (!containerID) {
				base.overlayContainer = jQuery('body');
				return;
			}

			let container;

			if (containerID instanceof jQuery) {
				container = containerID;
			} else if (containerID instanceof Element) {
				container = jQuery(containerID)
			} else if (typeof containerID === 'string') {
				container = jQuery(`#${containerID}`);
			} else {
				container = jQuery('body');
			}

			base.overlayContainer = container;
		}

		base.showLoading = function ()
		{
			if (base.options.loadingIconEnabled === true && typeof base.loadingIcon !== 'undefined')
			{
				base.loadingIcon.fadeIn('fast');
			}

			if (base.options.loadingOverlayEnabled && base.overlayContainer instanceof jQuery) {
				base.overlayContainer.LoadingOverlay('show', base.options.loadingOverlayEnabled);
			}
		};

		base.clearLoading = function ()
		{
			if (base.isRedirecting) {
				return;
			}

			if (base.options.loadingIconEnabled === true && typeof base.loadingIcon !== 'undefined')
			{
				base.loadingIcon.remove();
			}

			if (base.options.loadingOverlayEnabled && base.overlayContainer instanceof jQuery) {
				base.overlayContainer.LoadingOverlay('hide');
			}
		};

		base.init = function() {
			if (typeof(ajaxData) == "undefined" || ajaxData === null)
			{
				ajaxData = "";
			}

			if (ajaxData instanceof FormData)
			{
				ajaxData.set('tk', tk);
				ajaxData.set('tm', tm);
			}

			if (typeof(ajaxData) == "object")
			{
				ajaxData.tk = tk;
				ajaxData.tm = tm;
			}

			if (typeof(ajaxData) == "string")
			{
				ajaxData = ajaxData + '&tk=' + tk + '&tm=' + tm;
			}

			base.footerScripts = []; // Array to hold names of scripts that are dynamically loaded
			base.ajaxData = ajaxData;
			base.options = $.extend({}, $.SWLjs.ajax.defaultOptions, options);
			base.buildLoading();
			base.isRedirecting = base.options.isRedirecting ? base.options.isRedirecting : false;
		};

		base.beforeSend = function(jqXHR, settings) {
			if (typeof base.options.beforeSend == 'function')
			{
				var result = base.options.beforeSend(jqXHR, settings);

				if (result === false)
				{
					// Request was aborted before sending, remove corresponding reference to request so can fire fresh on next event
					base.$el.removeData("SWLjs.ajax");
					return result;
				}
			}

			jqXHR.setRequestHeader("X-Requested-With", "XMLHttpRequest");
			base.showLoading();
		};

		base.error = function(jqXHR, textStatus, errorThrown) {
			base.isRedirecting = false;
			base.clearLoading();

			if (typeof base.options.error == 'function')
			{
				return base.options.error(jqXHR, textStatus, errorThrown);
			}
			if (textStatus == "abort") {
				// manually aborted
			}
		};

		base.success = function(returnedData, textStatus, jqXHR) {
			base.successPreCallback(returnedData, textStatus, jqXHR);

			if (typeof(returnedData) == 'undefined' || returnedData == null)
			{
				return false;
			}

			if (typeof(returnedData.formToken) !== 'undefined' && typeof(returnedData.formTime) !== 'undefined')
			{
				refreshTokens(returnedData.formToken, returnedData.formTime);
			}

			if (typeof base.options.success == 'function')
			{
				return base.options.success(returnedData, textStatus, jqXHR);
			}

			if (typeof returnedData.error !== 'undefined')
			{
				base.isRedirecting = false;

				if (returnedData.error.length > 0)
				{
					base.options.errorMessageHandler(returnedData.error);
				}

				base.errorPostCallback(returnedData, textStatus, jqXHR);
				return false;
			}

			if (returnedData.message)
			{
				if (typeof(base.options.paginator) !== 'undefined')  // TODO: check paginator type to autoload
				{
					// TODO: allow more than 1 paginator to be automatically reloaded
					base.options.paginator.load();
				}

				base.options.successMessageHandler(returnedData.message);
			}

			if (base.options.autoParse)
			{
				base.parseResults(returnedData.data);
			}

			base.successPostCallback(returnedData, textStatus, jqXHR);

			if ($.trim(returnedData.forcedRedirect).length)
			{
				base.isRedirecting = true;
				window.location.href = returnedData.forcedRedirect;
			}
			else if (returnedData.handleRedirect)
			{
				base.isRedirecting = true;
				if (returnedData.handleRedirect == 'reload')
				{
					window.location.reload();
				}
				else
				{
					window.location.href = returnedData.handleRedirect;
				}
			}
		};

		base.complete = function(jqXHR, textStatus) {
			delete base.request;
			base.clearLoading();

			if (typeof base.options.complete == 'function')
			{
				return base.options.complete(jqXHR, textStatus);
			}
		};

		base.successPreCallback = function(data, textStatus, jqXHR) {
			if (typeof base.options.successPreCallback == 'function')
			{
				return base.options.successPreCallback(data, textStatus, jqXHR);
			}
		};

		base.successPostCallback = function(data, textStatus, jqXHR) {
			base.footerExtra(data, textStatus, jqXHR, function()
			{
				// Wait until footer extra is done before calling custom callback
				if (typeof base.options.successPostCallback == 'function')
				{
					return base.options.successPostCallback(data, textStatus, jqXHR);
				}
			});
		};

		base.errorPostCallback = function(data, textStatus, jqXHR) {
			if (typeof base.options.errorPostCallback == 'function')
			{
				return base.options.errorPostCallback(data, textStatus, jqXHR);
			}
		};

		base.parseResults = function(data)
		{
			base.$el.hide().html(Utf8.decode(data)).fadeIn();
		};

		base.footerExtra = function(data, textStatus, jqXHR, callback)
		{
			if (typeof(data.swl_footer_extra) === 'undefined' || typeof(base.$el) === 'undefined')
			{
				return callback();
			}

			try
			{
				var footer = JSON.parse(data.swl_footer_extra);
			}
			catch (e)
			{
				if (typeof base.options.successPostCallback == 'function')
				{
					return base.options.successPostCallback(data, textStatus, jqXHR);
				}
				else
				{
					return false;
				}
			}

			for (var key in footer)
			{
				if (key == 'js')
				{
					// Loop through all <script> tags and see if the script already exists before adding
					var scripts = document.getElementsByTagName('script');

					for (var jsKey in footer[key])
					{
						var exists = false;

						for (var i = 0; i < scripts.length; i++)
						{
							if (scripts[i].src.indexOf(jsKey) != -1)
							{
								exists = true;
								break;
							}
						}

						if (!exists)
						{
							var source = decodeURIComponent(footer[key][jsKey]);
							var newScript = document.createElement('script');
							newScript.setAttribute('type','text/javascript');
							newScript.setAttribute('src', source);

							if (newScript.addEventListener)
							{
								var verifyLoaded = function(event)
								{
									var source = '';

									if (typeof event.path !== 'undefined' && typeof event.path[0].src !== 'undefined')
									{
										source = event.path[0].src;
									}
									else if (typeof event.srcElement !== 'undefined' && event.srcElement.src !== 'undefined')
									{
										source = event.srcElement.src;
									}

									if (source != '')
									{
										// Remove source from array of footerScripts that still need to be loaded
										base.footerScripts.splice(base.footerScripts.indexOf(source), 1);
									}
								};

								base.footerScripts.push(source);
								newScript.addEventListener('load', verifyLoaded, false);
							}

							document.getElementsByTagName('head')[0].appendChild(newScript);
						}
					}
				}
				else if (key == 'css_core' || key == 'css_vendor')
				{
					var links = document.getElementsByTagName('links');

					for (var cssKey in footer[key])
					{
						var exists = false;

						for (var i = 0; i < links.length; i++)
						{
							if (links[i].href.indexOf(cssKey) != -1)
							{
								exists = true;
								break;
							}
						}

						if (!exists)
						{
							var newCss = document.createElement('link');
							newCss.setAttribute('rel', 'stylesheet');
							newCss.setAttribute('type', 'text/css');
							newCss.setAttribute('href', decodeURIComponent(footer[key][cssKey]));
							document.getElementsByTagName('head')[0].appendChild(newCss);
						}
					}
				}
				else if (key == 'extra')
				{
					for (var extraKey in footer[key])
					{
						if (document.documentElement.textContent.indexOf(extraKey) == -1)
						{
							// Not a duplicate footer so append to module
							base.$el.closest('div[data-module-name]').append(decodeURIComponent(footer[key][extraKey]));
						}
					}
				}
			}

			// Wait up to 6 seconds for scripts to actually be loaded before continuing
			var timeout = 60;
			poll = function (donePolling) {
				setTimeout(function () {
					timeout--;

					if (base.footerScripts.length > 0 && timeout > 0)
					{
						// Still waiting on some scripts to load
						poll(donePolling);
					}
					else
					{
						donePolling();
					}
				}, 100);
			};

			poll(callback);
		};

		var run = function() {
			base.request = new Date().getUTCMilliseconds();

			$.ajax({
				data: base.ajaxData,
				url: base.options.url,
				type: base.options.type,
				dataType: base.options.dataType,
				cache: base.options.cache,
				async: base.options.async,
				contentType: base.options.contentType,
				processData: base.options.processData,
				beforeSend: base.beforeSend,
				error: base.error,
				success: base.success,
				complete: base.complete
			});
		};

		// Run initializer
		base.init();

		// Run ajax call if it is not already running
		//if (typeof(base.$el.data("SWLjs.request")) == 'undefined')
		if (typeof base.request == 'undefined')
		{
			run();
		}
	};

	$.SWLjs.ajax.defaultOptions = {
		url: "/index.php",
		type: "POST",
		dataType: "json",
		cache: false,
		async: true,
		contentType: 'application/x-www-form-urlencoded; charset=UTF-8',
		autoParse: false,
		loadingIconEnabled: false,
		loadingOverlayEnabled: false,
		errorMessageHandler: function(message) {
			$.SWLjs.messageHandler(message, {"type": "error"});
		},
		successMessageHandler: function(message) {
			$.SWLjs.messageHandler(message, {"type": "message"});

			if (typeof loadIntersectionObserver === 'function') {
				loadIntersectionObserver();
			}
		}
	};

	$.fn.swljs_ajax = function(data, options) {
		if (this instanceof $)
		{
			//"this" is a jquery collection, do jquery stuff with it
			return this.each(function() {
				(new $.SWLjs.ajax(data, options, this));
			});

		} else {
			//"this" is not a jquery collection
			return new $.SWLjs.ajax(data, options);
		}
	};

	function buildOverlayIcon()	{
		const spinnerIcon = 'ball-fussion';
		const spinnerColor = '#000';

		addIconStyleSheet(spinnerIcon)

		const spinnerElement = document.createElement('div');
		spinnerElement.className = `la-${spinnerIcon}`;
		spinnerElement.style.color = spinnerColor;

		for (let i = 0; i < 4; i++) {
			const innerDiv = document.createElement('div');
			spinnerElement.appendChild(innerDiv);
		}

		return spinnerElement;
	}

	function addIconStyleSheet(spinnerIcon) {
		if (!spinnerIcon) return;

		const linkId = `loading-overlay-stylesheet-${spinnerIcon}`;
		const linkHref = `https://cdn.jsdelivr.net/npm/load-awesome@1.1.0/css/${spinnerIcon}.min.css`

		if (document.getElementById(linkId)) return;

		let link = document.createElement('link');
		link.rel = 'stylesheet';
		link.type = 'text/css';
		link.id = linkId;
		link.href = linkHref;

		document.getElementsByTagName('head')[0].appendChild(link);
	}
})(jQuery);
