var barColorJury = "#00C851";
var barColorAudience = "#ffc221";

var onupdate = function (from, to, percent) {
    var el = $(this.el)
    if (!el.data("locked") == 1)
        el.find('.percent').text(Math.round(percent) / 10 + "/10");
}
$(function () {
    $('.chart.jury').easyPieChart({
        barColor: barColorJury,
        trackColor: "#ffffff",
        scaleLength: 0,
        lineWidth: 7,
        lineCap: "round",
        onStep: onupdate
    });
    $('.chart.audience').easyPieChart({
        barColor: barColorAudience,
        trackColor: "#ffffff",
        scaleLength: 0,
        lineWidth: 7,
        lineCap: "round",
        onStep: onupdate
    });
});