
hehe = 1;
curind = 0;

function bclick() {
    document.getElementsByClassName("tempdisplay")[0].style.display="none";
    startTests();
    if (hehe != 1) {
        resumeRecording();
    }
}

function why() {
    $('.test'+ hehe).remove();
    hehe += 1;
    curind += 1;
    $("#includedContent").load("test_" + hehe + ".html");
}


w = window.innerWidth
setInterval(() => {
    if (Math.abs(window.innerWidth - w) > 200) {
        textbox = document.getElementsByClassName("tempdisplay")[0];
        textbox.style.display="block";
        textbox.getElementsByClassName('error')[0].textContent = "Do not resize or rotate the window or device while doing tests. This will invalidate the validity of the test.\nPlease reload the webpage to continue.\n\n進行測試時請勿調整視窗或設備的大小或旋轉視窗或設備。這將使測試的有效性失效。請重新加載網頁以繼續。";
        textbox.getElementsByClassName("yea")[0].textContent = "Reload";
        textbox.getElementsByClassName("yea")[0].onclick = function() { location.reload(); };
    }
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight * 0.7;
    fixsize();
});


st = "";
testdata = [[], [], [], [], []]
startTimes = []
function startTests() {
    startTimes.put(Date.now());
}

function finishTests() {
    textbox = document.getElementsByClassName("tempdisplay")[0];
    textbox.style.display="block";
    textbox.getElementsByClassName('error')[0].textContent = "This test has finished. Click Continue to go to the next test.";
    textbox.getElementsByClassName("yea")[0].textContent = "Continue ";
    textbox.getElementsByClassName("yea")[0].onclick = why;
}


let camera_stream = null;
let media_recorder = null;
let blobs_recorded = [];
let video = document.querySelector("#video");

function startRecording() {
    
	camera_stream = navigator.mediaDevices.getUserMedia({ video: true, audio: true });
	video.srcObject = camera_stream;

    
	media_recorder = new MediaRecorder(camera_stream, { mimeType: 'video/webm' });

    media_recorder.addEventListener('dataavailable', function(e) {
	    blobs_recorded.push(e.data);
	});

	media_recorder.addEventListener('stop', function() {
		let video_local = URL.createObjectURL(new Blob(blobs_recorded, { type: 'video/webm' }));
		download_link.href = video_local;
	});

}
function pauseRecording() {
    mediaRecorder.pause();
};

function resumeRecording() {
    mediaRecorder.resume();
};

function endRecording() {
	media_recorder.stop(); 
}