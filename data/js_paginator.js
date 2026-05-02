var JSPaginator = function(element, params, options, total) {
	var elem = jQuery(element);
	var scrollController = null; //scroll only
	var obj = this;
	var pagination = '';
	var paginationB = '';
	var contentContainer = '';
	var prevArea = '';
	var nextArea = '';
	var pTotal = total;
	var currentPage = 1;
	var overlay = jQuery('<div class="paginator-overlay moduleLoadingLarge" style="display:none;">&nbsp;</div>');
	var loaded = false;
	var running = false;
	var processing = false;
	var storedResults = {};
	var timeoutID = false;
	var pages = '';
	var direction = 'right';
	var rotateType = 'slide';
	var defaultLimit = 10;
	var paginationLocation = 'bottom';
	var sublist = false;
	var linkedOption = ''; // to update total on load
	var defaultOptions = {
		paginationType: 'more',
		pageID: "openAjax",
		format: 'json',
		buttonText: swl_pagination_translations["buttonText"] ? swl_pagination_translations["buttonText"] : 'More',
		storeResults: true,
		autoRotate: false,
		pShowNextPrev: true,
		pShowFirstLast: true,
		pShowRotate: true,
		pShowPages: true,
		pShowStep: true,
		maxResults: 0,
		delta: 2,
		pagPage: swl_pagination_translations["pagPage"] ? swl_pagination_translations["pagPage"] : 'Page',
		pagPages: swl_pagination_translations["pagPages"] ? swl_pagination_translations["pagPages"] : 'Pages',
		pagNext: swl_pagination_translations["pagNext"] ? swl_pagination_translations["pagNext"] : 'Next',
		pagNextPage: swl_pagination_translations["pagNextPage"] ? swl_pagination_translations["pagNextPage"] : 'Next Page',
		pagPrev: swl_pagination_translations["pagPrev"] ? swl_pagination_translations["pagPrev"] : 'Previous',
		pagPrevPage: swl_pagination_translations["pagPrevPage"] ? swl_pagination_translations["pagPrevPage"] : 'Previous Page',
		pagFirstPage: swl_pagination_translations["pagFirstPage"] ? swl_pagination_translations["pagFirstPage"] : 'First Page',
		pagLastPage: swl_pagination_translations["pagLastPage"] ? swl_pagination_translations["pagLastPage"] : 'Last Page',
		parseResults: function(returnedData)
		{
			config.preLoad();

			var data = decodeURIComponent(returnedData.data);

			if (config.paginationType == 'more'
				|| config.paginationType == 'scroll' || config.paginationType == 'infinite')
			{
				processing = true;

				// standard scroll
				if ((config.paginationType == 'scroll' || config.paginationType == 'infinite') && pagination)
				{
					pagination.before(data).ready(function()
					{
						config.contentLoaded();
						processing = false;
					});
				}
				else
				{
					// reload pagination using tabs or sort options
					if (config.paginationType == 'scroll')
					{
						elem.find('*').not('button.btn-pagination').remove();
					}

					elem.append(data).ready(function()
					{
						config.contentLoaded();
						processing = false;
					});
				}

				delete(data);
				return;
			}

			if (contentContainer.length > 0) {
				processing=true;
				var speed = 400;
				var slide_scale = 1000;
				var newElem = elem.clone(true);

				if (rotateType == 'fade') {
					newElem.hide();
					newElem.css('left',0);
				}
				else {
					elem.parent().css('overflow','hidden');
					if (direction == 'right') {
						newElem.css('left',slide_scale);
					} else {
						newElem.css('left',-(slide_scale));
					}
				}

				elem.css('position','relative');
				newElem.css('position','absolute');
				newElem.css('top',0);
				newElem.empty();

				newElem.append(data).ready(function() {
					config.contentLoaded();
					elem.after(newElem);

					if (rotateType == 'fade') {
						newElem.fadeIn(speed, function(){
							elem.remove();
							elem=newElem;
							elem.removeAttr('style');
							processing=false;
							obj.handleFooterExtra(returnedData);
						});
					} else {

						var pos = (direction == 'right') ?"-="+slide_scale : "+="+slide_scale;
						elem.animate({left:pos},speed);
						newElem.animate({left: "0"},speed,function() {
								elem.remove();
								elem=newElem;
								elem.removeAttr('style');
								delete newElem;
								processing=false;
								obj.handleFooterExtra(returnedData);
						});
					}
				});
			}
			else {
				elem.fadeOut('fast', function() {
					elem.empty();
					elem.append(data).ready(function() {
						config.contentLoaded();
						elem.fadeIn('fast');
						obj.formatPagination();
						processing=false;
						obj.handleFooterExtra(returnedData);
						jQuery(`div[data-max-results-reached="${elem.attr('id')}"]`).remove();

						if (returnedData.maxResultsReachedMessage) {
							elem.after(jQuery(`<div class="text-center" data-max-results-reached="${elem.attr('id')}">${returnedData.maxResultsReachedMessage}</div>`));
						}
					});
				});
			}

			delete(data);
		},
		errorMessageHandler:function(error)
		{
			elem.html(decodeURIComponent(error));
		},
		loadComplete: function(returnedData) {},
		contentLoaded: function() {
			// Fires on paginator.load as well as any paginate events
			if (typeof oembedsToIframely !== 'undefined') {
				oembedsToIframely(); // Render any newly added oembeds as iframes via iframely
			}
		},
		preLoad: function () {}
	};

	var config = jQuery.extend(defaultOptions, options || {});

	var defaultParams = {
		limit: defaultLimit,
		offset: 0
	}

	var urlParams = jQuery.extend(defaultParams, params || {});
	// pagination location override
	if (urlParams.limit > defaultLimit && options.paginationLocationNeverTop !== true)
	{
		paginationLocation = 'both';
	}

	var moduleName = (typeof(urlParams.module) !== 'undefined') ? urlParams.module.replace(/_/g, " ") : "";
	this.setParams = function(params) { urlParams = jQuery.extend(urlParams, params || {}); }

	this.getCurrentPage = function() { return currentPage; }

	this.getTotal = function() { return pTotal; }

	this.getParam = function(param) {
		if (typeof urlParams[param] === 'undefined') { return null; }
		return urlParams[param];
	}

	this.getPages = function() { return pages; }

	this.handleFooterExtra = function(data)
	{
		if (typeof(data.swl_footer_extra) !== 'undefined' && typeof(elem) !== 'undefined')
		{
			try
			{
				var footer = JSON.parse(data.swl_footer_extra);
			}
			catch (e)
			{
				return false;
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
							elem.closest('div[data-module-name]').append(decodeURIComponent(footer[key][jsKey]));
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
							elem.closest('div[data-module-name]').append(decodeURIComponent(footer[key][extraKey]));
						}
					}
				}
			}
		}
	}

	this.showLoading = function()
	{
		if (config.paginationType == 'scroll' || config.paginationType == 'infinite')
		{
			overlay.removeClass('moduleLoadingLarge');
			overlay.html('<span class="fas fa-spinner fa-pulse fa-lg paginator-loading-icon"></span>');
			elem.find('button.btn-pagination').hide();
		}
		else if (config.paginationType == 'more')
		{
			overlay.html('');
		}

		overlay.fadeIn('fast');

		if (typeof this.showCustomLoading == "function") { this.showCustomLoading(); }
	}

	this.hideLoading = function()
	{
		overlay.fadeOut('fast');

		if (config.paginationType == 'scroll' || config.paginationType == 'infinite')
		{
			elem.find('button.btn-pagination').show();
		}

		if (typeof this.hideCustomLoading == "function") { this.hideCustomLoading(); }
	}

	this.loadPaginationFromSessionStorage = function()
	{
		if (config.paginationType != "std" || config.paginationLocation == 'none'
			|| this.getModulelabel() == undefined)
		{
			return true;
		}

		var navigationType = window.performance.getEntriesByType("navigation")[0].type;

		if (navigationType === "back_forward" || navigationType === "reload")
		{
			var sessionItemsJson = sessionStorage.getItem(location.href);
			var sessionItems = {};
			var moduleKey = this.getModuleKey();

			if (sessionItemsJson != null)
			{
				sessionItems = JSON.parse(sessionItemsJson);
			}

			if (Object.keys(sessionItems).length > 0 && sessionItems[moduleKey] != undefined)
			{
				urlParams = sessionItems[moduleKey]['params'];
				loadPage(sessionItems[moduleKey]['page']);
				obj.setSearchQueryByParams();
				obj.createCurrentFiltersOnReloadByParams().then(function()
				{
					obj.setFiltersByParams();
					obj.setOrderByParams();
				});
			}
		}
	}

	this.setSearchQueryByParams = function()
	{
		var contextId = this.getContextId();
		var searchQueryInput = jQuery('#'+contextId+'_query');

		if (urlParams.search_query != undefined && urlParams.search_query.length > 0)
		{
			searchQueryInput.val(urlParams.search_query);
		}
	}

	this.createCurrentFiltersOnReloadByParams = function()
	{
		var contextId = this.getContextId();
		var filtersModalContainer = jQuery('#' + contextId + '_filter_modal .filter_container');
	
		return new Promise(function(resolve, _) {
			if (filtersModalContainer.length > 0
				|| urlParams.search_filters == undefined
				|| urlParams.search_filters.fields == undefined 
				|| Object.keys(urlParams.search_filters.fields).length == 0)
			{
				resolve();
				return;
			}

			var moduleSpecificAddModalFilterFunction = window[`addModalFilter_${contextId}`];
			if (typeof moduleSpecificAddModalFilterFunction === 'function') {
				var filtersToAddCount = Object.keys(urlParams.search_filters.fields).length;
				var filtersAddedCount = 0;

				var filterAddedCallback = function() {
					filtersAddedCount++;
					if (filtersAddedCount === filtersToAddCount) {
						resolve();
					}
				};

				for (var sideFilterType in urlParams.search_filters.fields) {
					var fieldId = "field_" + sideFilterType;
					moduleSpecificAddModalFilterFunction("#" + contextId + "_filter_modal .filters_container #filter_dropdown .dropdown-item[data-filter-id='" + fieldId + "']", true, filterAddedCallback);
				}
			}
		});
	};

	this.setActiveSideFiltersByParams = function()
	{
		var contextId = this.getContextId();
		var sideFiltersContainer = jQuery('#'+contextId+'_tableListTypeFilters');
		var filtersModalContainer = jQuery('#'+contextId+'_filter_modal .filter_container');

		if (urlParams.search_filters == undefined
			|| urlParams.search_filters.fields == undefined
			|| Object.keys(urlParams.search_filters.fields).length == 0)
		{
			return;
		}

		for (var sideFilterType in urlParams.search_filters.fields)
		{
			var fieldId = "field_"+sideFilterType;
			var selectedFilterValues = urlParams.search_filters.fields[sideFilterType];
			var sideFilterElement = sideFiltersContainer.find(".filter_value_select[data-filter-form-element='"+fieldId+"']");
			var filtersModalElement = filtersModalContainer.find(".filter_value_select[data-filter-form-element='"+fieldId+"']");

			if ((sideFilterElement.length > 0 || filtersModalElement.length > 0) && selectedFilterValues != undefined)
			{
				if (selectedFilterValues instanceof Map) {
					[...selectedFilterValues.keys()].forEach((selectedFilterValue) => {
						const { isChecked, isIndeterminate } = selectedFilterValues.get(selectedFilterValue);
						filtersModalElement.find(`[value="${selectedFilterValue}"]`).prop('checked', isChecked).prop('indeterminate', isIndeterminate);
						sideFilterElement.find(`[value="${selectedFilterValue}"]`).prop('checked', isChecked).prop('indeterminate', isIndeterminate);
					});
				} else {
					// select or text
					filtersModalElement.val(selectedFilterValues);
					sideFilterElement.val(selectedFilterValues);
					sideFilterElement.trigger('js_paginatorFilterUpdate', { contextId, fieldId, value: selectedFilterValues });
				}
			}
		}

		var moduleSpecificAddActiveFiltersFunction = window[`addActiveFilters_${contextId}`];
		if (typeof moduleSpecificAddActiveFiltersFunction === 'function') {
			moduleSpecificAddActiveFiltersFunction(urlParams);
		}
	}

	this.setFiltersByParams = function()
	{
		var contextId = this.getContextId();
		var quickFiltersModalContainer = jQuery('#'+contextId+'_filter_modal .modal-body .quick_filters');
		var sideFiltersContainer = jQuery('#'+contextId+'_quickFilters');

		if (urlParams.active_quick_filters != undefined && Object.keys(urlParams.active_quick_filters).length > 0)
		{
			quickFiltersModalContainer.find("button.quick_filter.active").removeClass('btn-secondary active').addClass('btn-outline-secondary');

			for (var filterType in urlParams.active_quick_filters)
			{
				for (var filterId in urlParams.active_quick_filters[filterType])
				{
					quickFiltersModalContainer.find(".quick_filter[data-filter-type='"+filterType+"'][data-filter-id='"+filterId+"']").addClass('active');
					sideFiltersContainer.find(".quick_filter[data-filter-type='"+filterType+"'][data-filter-id='"+filterId+"']").addClass('active');
				}
			}
		}

		if (urlParams.inactive_quick_filters != undefined && Object.keys(urlParams.inactive_quick_filters).length > 0)
		{
			for (var inactiveFilterType in urlParams.inactive_quick_filters)
			{
				for (var inactiveFilterId in urlParams.inactive_quick_filters[inactiveFilterType])
				{
					quickFiltersModalContainer.find(".quick_filter[data-filter-type='"+inactiveFilterType+"'][data-filter-id='"+inactiveFilterId+"']").removeClass('btn-secondary active').addClass('btn-outline-secondary');
					sideFiltersContainer.find(".quick_filter[data-filter-type='"+inactiveFilterType+"'][data-filter-id='"+inactiveFilterId+"']").removeClass('btn-secondary active').addClass('btn-outline-secondary');
				}
			}
		}

		this.setActiveSideFiltersByParams();
	}

	this.setOrderByParams = function()
	{
		var contextId = jQuery(elem.context).attr('id');

		if (urlParams.orderBy != undefined)
		{
			var orderByContainer = jQuery('#'+contextId+'_order_by div.dropdown-menu');
			var sortItem = orderByContainer.find('.dropdown-item[data-order-by="'+urlParams.orderBy+'"]');
			var sortItemlabel = jQuery(sortItem[0]).text();
			orderByContainer.find('.dropdown-item').find('span.fas.fa-check').remove();
			jQuery(sortItem[0]).prepend('<span class="fas fa-check mr-1"></span>');
			jQuery('#'+contextId+'_order_by [data-toggle="dropdown"]').attr('aria-label',sortItemlabel).text(sortItemlabel);
		}

		if (urlParams.sortOrder != undefined)
		{
			if (urlParams.sortOrder == 'desc' && !jQuery('#'+contextId+'_sort_order').hasClass('fa-arrow-down'))
			{
				jQuery('#'+contextId+'_sort_order').removeClass('fa-arrow-up').addClass('fa-arrow-down');
			}
			else if (urlParams.sortOrder == 'asc' && !jQuery('#'+contextId+'_sort_order').hasClass('fa-arrow-up'))
			{
				jQuery('#'+contextId+'_sort_order').removeClass('fa-arrow-down').addClass('fa-arrow-up');
			}
		}
	}

	this.showPagination = function() {
		showPagination();
	}

	this.init = function() {
		showPagination();
		if (config.paginationType == 'rotate'){
			obj.formatPagination();
		}

		this.loadPaginationFromSessionStorage();
	}

	this.clearPagination = function ()
	{
		currentPage = 1;
		if (pagination instanceof jQuery) {

			if (config.paginationType == 'rotate')
			{
				//nested elements
				elem.unwrap().unwrap().unwrap();
			}

			elem.siblings('.pager-nav').remove();
			elem.siblings('.blockspacer').remove();
			elem.siblings('.paginator-overlay').remove();

			if (config.paginationType == 'scroll' || config.paginationType == 'infinite')
			{
				if (scrollController)
				{
					scrollController = scrollController.destroy(true);
				}
			}

			pagination.remove();
			pagination = '';
		}

		if (paginationB instanceof jQuery) {
			paginationB.remove();
			paginationB = '';
		}

		// remove time out
		handleClick();
	}

	this.load = function(checkHistory = true)
	{
		if (checkHistory == true && location.hash !="" && Object.keys(storedResults).length == 0)
		{
			this.init();
		}
		else
		{
			urlParams.offset = 0;
			storedResults = {};
			handleClick();
			getData();
		}
	}

	this.formatPagination = function() {
		var elHeight = elem.parent().outerHeight();
		if (prevArea.length > 0) {
			var pHeight = prevArea.outerHeight();
			prevArea.css('top', (elHeight / 2) - (pHeight / 2) + 'px');
		}
		if (nextArea.length > 0) {
			var nHeight = prevArea.outerHeight();
			nextArea.css('top', (elHeight / 2) - (nHeight / 2) + 'px');
		}
	}

	this.getModulelabel = function()
	{
		var currentModuleSel = elem.context;
		var label = jQuery(currentModuleSel).closest('div.module').find('header h2').text();

		if (label == "")
		{
			label = jQuery(currentModuleSel).closest('div.module_container').find('div.boxsitepage p').text();
		}


		if (label == "")
		{
			var moduleContainer = jQuery(currentModuleSel).closest('div.module_container');
			var moduleName = jQuery(moduleContainer).attr('data-module-name');
			var moduleColumn = jQuery(moduleContainer).attr('data-module-column');
			var moduleOrder = jQuery(moduleContainer).attr('data-module-row');

			label = moduleName;

			if (label != undefined && moduleColumn != 0 && moduleOrder != 0)
			{
				label = label + moduleColumn + moduleOrder;
			}
		}

		return label;
	}

	this.getModuleHash = function()
	{
		var moduleLabel = this.getModulelabel();
		return moduleLabel.replace(/[^a-z0-9]+/gi,'-').toLowerCase();
	}

	this.getModuleKey = function()
	{
		let currentModuleSel = elem.context;
		let moduleKey = jQuery(currentModuleSel).closest('div.module').attr('id');

		if (typeof moduleKey === 'undefined' || moduleKey == '') {
			moduleKey = this.getModuleHash();
		}

		return moduleKey;
	}

	this.getContextId = function()
	{
		return jQuery(elem.context).attr('id').replace(/_data$/, '');
	}

	this.pushIntoSessionStorage = function(page = 1)
	{
		var moduleLabel = this.getModulelabel();

		if (config.paginationType != "std" || config.paginationLocation == 'none'
			|| this.getPages().length == 0
			|| moduleLabel == undefined
			)
		{
			return true;
		}
		else if (page == null && (urlParams.active_quick_filters != undefined || urlParams.inactive_quick_filters != undefined || urlParams.search_query != undefined))
		{
			page = 1;
		}

		var moduleKey = this.getModuleKey();

		if (moduleKey != "")
		{
			var currentURL = String(location.href);
			var currentPage = page;
			var url = currentURL;

			var itemJson = sessionStorage.getItem(url);
			var itemVal = {};

			if (itemJson != null)
			{
				itemVal = JSON.parse(itemJson);
			}

			var itemCount = Object.keys(itemVal).length;

			if (itemCount > 0 && itemVal[moduleKey] != undefined)
			{
				itemVal[moduleKey]['page'] = currentPage;
			}
			else
			{
				itemVal[moduleKey] = {};
				itemVal[moduleKey]['page'] = currentPage;
			}

			var objCount = Object.keys(itemVal).length;

			if (objCount > 0 )
			{
				itemVal[moduleKey]['params'] = urlParams;
				sessionStorage.setItem(url, JSON.stringify(itemVal));

			}
		}
	}

	var loadPage = function(page) {
		direction = (page > obj.getCurrentPage()) ? "right" : "left";
		const offset = ((page - 1) * urlParams.limit);
		obj.setParams({'offset': offset});
		getData();
	}

	var storeResults = function(returnedData, page) { storedResults[page] = returnedData; }

	var processData = function(data) {
		config.parseResults(data);
		urlParams.offset = Number(urlParams.offset) + Number(urlParams.limit);
		showPagination();
		obj.hideLoading();
		config.loadComplete(data);
		return true;
	}

	// Private method - can only be called from within this object
	var getData = function() {
		if (!config.autoRotate){
			obj.showLoading();
		}

		obj.setParams({'page_id': config.pageID, 'tk': tk, 'tm': tm});
		if (running || processing) { return false; }
		running = true;

		if (config.autoRotate || config.storeResults) {
			page = Math.floor((Number(urlParams.offset) + Number(urlParams.limit)) / Number(urlParams.limit));

			if (page in storedResults) {
				processData(storedResults[page]);
				obj.pushIntoSessionStorage(page);
				running = false;
				return;
			}
		}

		if (!loaded) { obj.setParams({'ajaxType': 'paginate'}); }
		else { delete urlParams['ajaxType']; }

		jQuery.ajax(
		{
			url: '/index.php',
			data: urlParams,
			type: 'POST',
			dataType: config.format,
			beforeSend: function()
			{
				setLoadingState(options);
			},
			error: function(xhr, ajaxOptions, thrownError)
			{
				obj.hideLoading();
				showSitePageNotification('error', 'An error occurred, please try again');
			},
			success: function(returnedData)
			{
				loaded = true;

				if (typeof(returnedData) !== 'undefined' && returnedData)
				{
					if (returnedData.formToken && returnedData.formTime)
					{
						refreshTokens(returnedData.formToken, returnedData.formTime);
					}

					if (typeof(returnedData.error) !== 'undefined' && returnedData.error)
					{
						config.errorMessageHandler(returnedData.error);
						return false;
					}

					var dataToDecode = this.data.replace(/&/g, "\",\"").replace(/=/g,"\":\"")
							.replace(/%22/g, "%5C%22").replace(/%24/g, "$");
					var qStr = JSON.parse('{"' + decodeURI(dataToDecode) + '"}');
					var servedPage = Math.floor((Number(qStr.offset) + Number(qStr.limit)) / Number(qStr.limit));

					if (config.storeResults) {storeResults(returnedData, servedPage);}

					if (returnedData.total != null)
					{
						pTotal = Number(returnedData.total);

						if (obj.linkedOption != undefined)
						{
							var optionElem = jQuery("span[data-option-name='" + obj.linkedOption + "']");

							if (optionElem != undefined)
							{
								var optionText = optionElem.text();

								if (optionText.match(/\d+/))
								{
									optionElem.text(optionText.replace(/\d+/, pTotal > 0 ? pTotal : ""));
								}
								else if (pTotal > 0)
								{
									optionElem.text(returnedData.total + optionElem.text());
								}
							}
						}
					}

					processData(returnedData);
					obj.pushIntoSessionStorage(servedPage);
				}
			},
			complete: function(returnedData) {
				running = false;
				clearLoadingState(options);
			}
		});
	};

	var setLoadingState = function({ elementsToDisplayLoadingOverlay = [], elementsToDisableDuringLoading = [] })
	{
		elementsToDisplayLoadingOverlay.forEach(function(elementToDisplayLoadingOverlay) {
			if (jQuery(elementToDisplayLoadingOverlay).find('.loading-wrapper').length > 0) {
				jQuery(elementToDisplayLoadingOverlay).find('.loading-wrapper').show();
			}
			else {
				jQuery(elementToDisplayLoadingOverlay)
					.css({'position' : 'relative'})
					.append('<div class="loading-wrapper"><div class="loading-overlay"><span class="fas fa-spinner fa-pulse fa-2x"></span></div></div>');
			}
		});

		elementsToDisableDuringLoading.forEach(function(elementToDisableDuringLoading) {
			if (jQuery(elementToDisableDuringLoading).is("button")) {
				jQuery(elementToDisableDuringLoading).prop("disabled", true);
			}
			else {
				jQuery(elementToDisableDuringLoading).hide();
			}
		});

	}

	var clearLoadingState = function({ elementsToDisplayLoadingOverlay = [], elementsToDisableDuringLoading = [] })
	{
		elementsToDisplayLoadingOverlay.forEach(function(elementToDisplayLoadingOverlay){
			if (jQuery(elementToDisplayLoadingOverlay).find('.loading-wrapper').length > 0) {
				jQuery(elementToDisplayLoadingOverlay).find('.loading-wrapper').remove();
			}
		});

		elementsToDisableDuringLoading.forEach(function(elementToDisableDuringLoading) {
			if (jQuery(elementToDisableDuringLoading).is("button")) {
				jQuery(elementToDisableDuringLoading).prop("disabled", false);
			}
			else {
				jQuery(elementToDisableDuringLoading).show();
			}
		});
	};

	var handleClick = function()
	{
		if (timeoutID)
		{
			clearTimeout(timeoutID);
			timeoutID = false;
		}

		return true;
	};

	var rotate = function () {
		var totalResults = pTotal;

		if (config.maxResults && pTotal > config.maxResults)
		{
			totalResults = config.maxResults;
		}

		var totalPages = urlParams.limit ? Math.ceil(pTotal / urlParams.limit) : 0;

		if (currentPage == totalPages) { loadPage(1); }
		else { loadPage(currentPage + 1); }

		return true;
	};

	var setScrollHeight = function()
	{
		if (currentPage == 1)
		{
			elem.height('auto');
		}

		if (elem.height() === 0)
		{
			elem.height((50 * urlParams.limit) + 25);
		}
		else
		{
			elem.height(elem.height() * 0.98);
		}

		if (config.paginationType == 'infinite')
		{
			elem.height('unset');
		}
	};

	var showPagination = function()
	{
		if (config.paginationLocation == 'none')
		{
			return true;
		}

		var totalResults = pTotal;

		if (config.maxResults && pTotal > config.maxResults)
		{
			totalResults = config.maxResults;
		}

		var totalPages = urlParams.limit ? Math.ceil(totalResults / urlParams.limit) : 0;

		if (totalResults <= 0 || totalPages == 1
			|| ((config.paginationType == 'more' || config.paginationType == 'scroll' || config.paginationType == 'infinite') && Number(urlParams.offset) >= totalResults))
		{
			obj.clearPagination();

			if (totalResults <= 0 || totalPages == 1)
			{
				elem.height('auto');

				if (elem[0].SimpleBar)
				{
					jQuery(elem[0]).removeAttr('data-simplebar');
					jQuery(elem[0]).css('overflow-y', 'inherit');
				}
			}

			return true;
		}

		currentPage = Math.floor(urlParams.offset / urlParams.limit);

		if (config.paginationType != 'more' && config.paginationType != 'scroll')
		{
			// init regular pagination
			delta = config.delta;
			var showPages = (delta * 2) + 1;
		}

		if (!(pagination instanceof jQuery))
		{
			if (config.paginationType == 'more')
			{
				// create more pagination
				let moreClasses = config.sublist ? 'btn-pagination ml-5 mb-3' : 'btn-pagination';
				pagination = jQuery('<a href="javascript:void(0);" type="button" data-paginator=true class="' + moreClasses + '"></a>');

				pagination.bind("click", function(event, ui)
				{
					handleClick();
					getData();
				});

				pagination.text(config.buttonText);

				if (paginationLocation == 'bottom' || paginationLocation == 'both') {
					elem.after(pagination);
					elem.after(overlay);
					elem.after(jQuery('<div class="blockspacer"></div>'));
				}

				if (paginationLocation == 'both') {
					paginationB = pagination.clone(true, true).addClass('top-pagination');
					elem.before(paginationB);
					elem.before(jQuery('<div class="blockspacer"></div>'));
				}

				return true;
			}

			if ((config.paginationType == 'scroll' || config.paginationType == 'infinite') && !scrollController)
			{
				if (config.paginationType == 'scroll')
				{
					elem.css('overflowY', 'scroll');
					elem.addClass('paginator-scroll-area');
				}

				pagination = jQuery('<button type="button" id="' + elem.attr('id') + '_loader" data-paginator=true class="btn btn-primary btn-sm btn-block btn-pagination paginator-scroll-button"></button>');
				pagination.text(config.buttonText);

				if (elem.find('.btn-pagination').length > 0)
				{
					pagination = elem.find('button.btn-pagination');
					pagination.show();
				}

				elem.append(pagination);
				elem.after(overlay);
				elem.after(jQuery('<div class="blockspacer"></div>'));

				pagination.on("click", function(event, ui)
				{
					pagination.fadeOut('fast', function()
					{
						handleClick();
						getData();
					});
				});

				if (elem[0])
				{
					if (config.paginationType == 'scroll')
					{
						// init scroll bar
						var sBar = new SimpleBar(elem[0]);
						sBar.recalculate();
						var scrollElement = sBar.getScrollElement();

						// init controller
						scrollController = new ScrollMagic.Controller({container: scrollElement});
					}
					else
					{
						scrollController = new ScrollMagic.Controller();
					}

					if (pagination[0])
					{
						// build scene
						var scene = new ScrollMagic.Scene({
							offset: -10,
							triggerElement: pagination[0],
							triggerHook: "onEnter"})
								.addTo(scrollController)
								.on("enter", function(e)
								{
									handleClick();
									getData();
								});
					}
				}

				elem.ready(function()
				{
					if (elem.find('img').length > 0)
					{
						elem.find('img').on('load', function()
						{
							setScrollHeight();
						}).each(function()
						{
							if (this.complete)
							{
								jQuery(this).trigger('load');
							}
						});
					}
					else
					{
						setScrollHeight();
					}
				});

				return true;
			}

			if (config.paginationType == 'rotate') // create rotator pagination
			{
				pagination = jQuery('<div /></div>').addClass('pagination rotate-pagination').data('paginator',true);
				prevArea = jQuery('<div /></div>').addClass('paginator_container pager-nav').css('left', '4px').css('position', 'absolute').css('display', 'none').css('z-index', '99');
				nextArea = jQuery('<div /></div>').css('right', '4px').addClass('paginator_container pager-nav').css('position', 'absolute').css('display', 'none').css('z-index', '99');

				if (config.pShowRotate) {
					this.prevButton = jQuery('<div /></div>').addClass('pager-item pager-left');
					this.nextButton = jQuery('<div /></div>').addClass('pager-item pager-right');

					prevArea.append(this.prevButton);
					nextArea.append(this.nextButton);

					elem.parent().parent().mouseover(function() {
						prevArea.show();
						nextArea.show();
					});
					elem.parent().parent().mouseout(function() {
						prevArea.hide();
						nextArea.hide();
					});
				}

				elem.wrap(pagination).wrap(jQuery('<div /></div>').addClass('paginator_wrapper').css('position', 'relative')).wrap(jQuery('<div /></div>').addClass("paginator_container content-container").css('position', 'relative'));
				pagination = elem.parent().parent();
				contentContainer = elem.parent();
				contentContainer.before(prevArea);
				contentContainer.after(nextArea);
				var insertionPoint = pagination;
			}
			else
			{
				var insertionPoint = elem;
			}

			if (config.paginationType != 'rotate' || config.pShowPages)
			{
				// create regular pagination
				var pagePagination = jQuery('<div class="pagination paginator-pagination"></div>');
				if (config.paginationType != 'rotate') {
					pagePagination.data('data-pagination', true);
					pagination = pagePagination;
				}

				if (paginationLocation == 'both') {
					paginationB = pagePagination.clone(true, true).addClass('top-pagination');
					paginationB.insertBefore(insertionPoint);
					insertionPoint.before(jQuery('<div class="blockspacer"></div>'));
				}

				if (paginationLocation == 'bottom' || paginationLocation == 'both') {
					pagePagination.insertAfter(insertionPoint);
					insertionPoint.after(overlay);
					insertionPoint.after(jQuery('<div class="blockspacer"></div>'));
				}

				if (config.paginationType == 'rotate') { pagination = pagePagination; }
			}

			if (config.autoRotate) {
				timeoutID = setInterval(function() {
					rotate();
				}, (config.autoRotate * 1000));
			}
		}

		//PAGINATION EXISTS

		if (config.paginationType == 'more' || config.paginationType == 'scroll' || config.paginationType == 'infinite')
		{
			return true;
		}
		else if (config.paginationType == 'rotate' && config.pShowRotate) {
			this.prevButton.unbind('click').bind("click", function(event) {
				handleClick();
				if (!jQuery(this).hasClass("pager-disabled")) {
					var rNum = (currentPage == 1) ? totalPages : currentPage - 1;
					loadPage(rNum);
				}
			});

			this.nextButton.unbind('click').bind("click", function(event) {
				handleClick();
				if (!jQuery(this).hasClass("pager-disabled")) {
					var rNum = (currentPage == totalPages) ? 1 : currentPage + 1;
					loadPage(rNum);
				}
			});
		}

		if (pages.length > 0) { pages.remove(); }

		pages = jQuery('<div class="pager-pages pager-continer paginator_container">');
		var start = 1;
		var end = showPages;

		if (showPages > totalPages) {
			start = 1;
			end = totalPages;
		}
		else if ((currentPage + delta) > totalPages) {
			start = totalPages - showPages + 1;
			end = totalPages;
		}
		else if (currentPage > delta) {
			start = currentPage - delta;
			end = start + showPages - 1;
		}

		if (config.pShowPages) {
			for (var pNum = start; pNum <= end; pNum++) {
				if (pNum == currentPage) {
					pages.append(jQuery('<span aria-label="' + moduleName + ' ' + config.pagPage + ' ' + pNum + '" class="pager-num pager-item pager-item-' + pNum + '">' + pNum + '</span>'));
				}
				else {
					pages.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagPage + ' ' + pNum + '" href="javascript:void(0)" class="pager-num pager-item pager-item-' + pNum + '">' + pNum + '</a>').bind("click", {'page': pNum}, function(event) {
						event.preventDefault();
						handleClick();
						loadPage(event.data.page);
					}));
				}
			}
		}

		if (config.paginationType == 'rotate') {
			var insertionPoint = elem.parent().parent();
			var pagePagination = insertionPoint.siblings('.paginator-pagination').first();
		}
		else {
			var insertionPoint = elem;
			var pagePagination = pagination;
		}

		pagePagination.empty();

		if (config.pShowFirstLast || config.pShowNextPrev) {
			var lJump = jQuery('<div class="pager-left-nav pager-continer paginator_container">');

			if (currentPage == 1) {
				if (config.pShowFirstLast) {
					lJump.append(jQuery('<span aria-label="' + moduleName + ' ' + config.pagFirstPage + '" class="pager-left-first pager-item pager-left">&lt;&lt;</span> '));
				}
				if (config.pShowNextPrev) {
					lJump.append(jQuery('<span aria-label="' + moduleName + ' ' + config.pagPrevPage + '" class="pager-left-prev pager-item pager-left">&lt;</span>'));
				}
			}
			else
			{
				if (config.pShowFirstLast) {
					lJump.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagFirstPage + '" href="javascript:void(0)" class="pager-left-first pager-item pager-left">&lt;&lt;</a>').bind("click", function(event)
					{
						event.preventDefault();
						handleClick();
						loadPage(1);
					}));
				}

				if (config.pShowNextPrev){
					lJump.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagPrevPage + '" href="javascript:void(0)" class="pager-left-prev pager-item pager-left">&lt;</a>').bind("click", {'page': (currentPage - 1)}, function(event)
					{
						event.preventDefault();
						handleClick();
						loadPage(event.data.page);
					}));
				}
			}

			pagePagination.append(lJump);
		}

		if (config.pShowStep) {
			var lElips = jQuery('<div class="pager-left-ellipsis pager-continer paginator_container">');

			if (totalPages > showPages && currentPage > delta + 1) {
				step = (start - delta - 1);
				if (step <= 0) { step = 1 + delta; }
				var numPages = showPages >= (currentPage - delta) ? (currentPage + delta) - showPages : showPages;

				lElips.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagPrev + ' ' + numPages + ' ' + config.pagPages + '" href="javascript:void(0)" class="pager-left-step pager-item">&hellip;</a>').bind("click", {'page': step}, function(event) {
					event.preventDefault();
					handleClick();
					loadPage(event.data.page);
				}));
			}

			var rElips = jQuery('<div class="pager-right-ellipsis pager-continer paginator_container">');

			if (totalPages > showPages && (totalPages - currentPage) > delta) {
				step = (end + delta + 1);
				if (step >= totalPages) { step = totalPages - delta; }
				var numPages = (showPages + currentPage + delta) >= totalPages ? totalPages - (currentPage + delta) : showPages;

				rElips.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagNext + ' ' + numPages + ' ' + config.pagPages + '"  href="javascript:void(0)" class="pager-right-step pager-item">&hellip;</a>').bind("click", {'page': (step)}, function(event) {
					event.preventDefault();
					handleClick();
					loadPage(event.data.page);
				}));
			}
			pagePagination.append(lElips, pages, rElips);
		}
		else {
			pagePagination.append(pages);
		}

		if (config.pShowFirstLast || config.pShowNextPrev) {
			var rJump = jQuery('<div class="pager-right-jump pager-continer paginator_container">');
			if (currentPage == totalPages) {
				if (config.pShowNextPrev) {
					rJump.append(jQuery('<span aria-label="' + moduleName + ' ' + config.pagNextPage + '" class="pager-right-next pager-item pager-right">&gt;</span> '));
				}
				if (config.pShowFirstLast) {
					rJump.append(jQuery(' <span aria-label="' + moduleName + ' ' + config.pagLastPage + '" class="pager-right-end pager-item pager-right">&gt;&gt;</span>'));
				}
			}
			else {
				if (config.pShowNextPrev) {
					rJump.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagNextPage + '" href="javascript:void(0)" class="pager-right-next pager-item pager-right">&gt;</a>').bind("click", {'page': (currentPage + 1)}, function(event) {
						event.preventDefault();
						handleClick();
						loadPage(event.data.page);
					}));
				}

				if (config.pShowFirstLast) {
					rJump.append(jQuery('<a aria-label="' + moduleName + ' ' + config.pagLastPage + '" href="javascript:void(0)" class="pager-right-end pager-item pager-right">&gt;&gt;</a>').bind("click", {'page': (totalPages)}, function(event) {
						event.preventDefault();
						handleClick();
						loadPage(event.data.page);
					}));
				}
			}

			pagePagination.append(rJump);
		}

		if (paginationLocation == 'both') {
			var pageBclone = pagePagination.clone(true, true).addClass('top-pagination');
			paginationB.replaceWith(pageBclone);
			paginationB = pageBclone;
		}
	};

	if (typeof total != 'undefined') { 	obj.init(); }
};

jQuery.fn.jsPaginator = function(params, options, total) {
	return this.each(function() {
		var element = jQuery(this);

		// Return early if this element already has a plugin instance
		if (element.data('jsPaginator')) { return; }

		// pass options to plugin constructor
		var jsPaginator = new JSPaginator(this, params, options, total);
		// Store plugin object in this element's data
		element.data('jsPaginator', jsPaginator);

	});
};
