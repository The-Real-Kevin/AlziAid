function includeEssentials2() {
    var elements = document.getElementsByClassName("showbox");

    for (var i = 0; i < elements.length; i++) {

        var element = elements[i];

        var newElement = document.createElement("button");
        var newElement2 = document.createElement("button");
        var div = document.createElement("div");

        var textNode = document.createTextNode("View More");
        var textNode2 = document.createTextNode("Visit");

        newElement.style.borderRadius = "0px";
        newElement.style.borderTopLeftRadius = "10px"; 
        newElement.style.borderBottomLeftRadius = "10px";
        newElement.style.color = "white";
        newElement2.style.borderRadius = "0px";
        newElement2.style.borderTopRightRadius = "10px"; 
        newElement2.style.borderBottomRightRadius = "10px";
        newElement2.style.color = "white";
        div.style.paddingTop = "13px"
        div.style.paddingLeft = "10px"

        newElement.appendChild(textNode);
        newElement2.appendChild(textNode2);
        
        div.appendChild(newElement);
        div.appendChild(newElement2);

        element.appendChild(div);
    }
}
