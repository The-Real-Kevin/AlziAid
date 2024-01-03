function toggleDropdown(show) {
  var dropdownContent = document.querySelector(".dropdown-content");
  if (show) {
    setTimeout(function () {
      dropdownContent.style.opacity = 1;
      dropdownContent.style.transform = "translateY(0)";
    }, 10);
  } else {
    dropdownContent.style.opacity = 0;
    dropdownContent.style.transform = "translateY(-250px)";
  }
}
document.addEventListener('click', function (event) {
  var dropdownContent = document.querySelector('.dropdown-content');
  var w3Button = document.querySelector('.w3-button');

  // Check if the clicked element is neither the dropdown content nor the button
  if (!dropdownContent.contains(event.target) && !w3Button.contains(event.target)) {
    toggleDropdown(false);
  }
});


function w3_open() {
  document.getElementById("mySidebar").style.display = "block";
}

function w3_close() {
  var sidebar = document.getElementById("mySidebar");
  sidebar.classList.add("w3-animate-left-close"); // Add animation class
  setTimeout(function () {
    sidebar.style.display = "none"; // Hide sidebar after animation
    sidebar.classList.remove("w3-animate-left-close"); // Remove animation class
  }, 200);
}

function get_title() {
  ez = window.location.href.split("/");
  ez = ez[ez.length - 1];
  ez = ez.replace('.html', '')
  words = ez.split("#")[0].split("_");

  for (let i = 0; i < words.length; i++) {
    words[i] = words[i][0].toUpperCase() + words[i].substr(1);
  }

  words = words.join(" ");
  return words
}
function includeEssentials() {
  $("#includeHtml").load("./../essentials.html");
}
function do_verify() {
  const sessionCookie = document.cookie.split(';').find(cookie => cookie.startsWith('session='));
  if (sessionCookie) {
    const sessionId = sessionCookie.split('=')[1];
    const checkSessionUrl = `https://expsrv.isf.edu.hk/auth/checksession?id=${sessionId}`;
    fetch(checkSessionUrl)
      .then(response => response.json())
      .then(data => {
        if (data === false) {
          window.location.href = './../login.html';
        }
      })
      .catch(error => {
        console.error('Error:', error);
        window.location.href = './../login.html';
      });
  } else {
    window.location.href = './../login.html';
  }
}

function run_instant() {
  document.title = get_title() + " | ISF World Expo"

  

  //do_verify()
}

run_instant()

window.onload = includeEssentials;


