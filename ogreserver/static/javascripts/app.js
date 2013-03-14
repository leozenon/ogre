$(document).ready(function() {
	$(".rating").each(function(index, item) {
		var id = $(item).text();
		$(item).empty();
		getRating(id, item);
	})
	$(".comments").each(function(index, item) {
		var id = $(item).text();
		$(item).empty();
		getRating(id, item);
	})
})

$(document).on('ajaxBeforeSend', function(e, xhr, options) {
	var element = $(e.srcElement)
	element.removeClass("hidden");
	$('<img src="/static/images/loading.gif">')
		.appendTo(element)
		.hide()
		.fadeIn("fast");
})

function getRating(id, element) {
	$.ajax({
		type: 'GET',
		url: '/ajax/rating/'+id,
		dataType: 'json',
		timeout: 20000,
		context: $(element),
		success: function(data){
			// context means 'this' is the element
			if(data.rating) {
				this.text(data.rating);
			}else{
				this.text("-");
			}
		},
		error: function(xhr, options, error){
			console.log("rating error: "+error);
		}
	})
}

function getComments(id, element) {
	$.ajax({
		type: 'GET',
		url: '/ajax/comment-count/'+id,
		dataType: 'json',
		timeout: 20000,
		context: $(element),
		success: function(data){
			// context means 'this' is the element
			if(data.rating) {
				this.text(data.comments);
			}else{
				this.text("-");
			}
		},
		error: function(xhr, options, error){
			console.log("comments error: "+error);
		}
	})
}
