var app = new Vue({
	el: '#app',
	data: {
		scanner: null,
		activeCameraId: null,
		activeServiceId: null,
		cameras: [],
		services: [],
		scans: []
	},
	mounted: function () {
		var self = this;
		self.scanner = new Instascan.Scanner({ video: document.getElementById('preview'), scanPeriod: 5 });
		self.scanner.addListener('scan', function (content, image) {
			self.scans.unshift({ date: +(Date.now()), content: content });
			// Created a URL object using URL() method 
			var parser = new URL(content); 
			if (self.activeServiceId){
				if(parser.protocol=="https:" && (parser.host=="t.me"||parser.host=="telegram.me")){
					var botName=parser.pathname
					console.log("botName",botName); 
					if (botName){
						newURL="https://t.me/"+self.services[self.activeServiceId].bot+"?start="+botName.substr(1)
						console.log('newURL',newURL)
						window.open( 
              newURL,"_self")
					}
				}
			}
		});
		Instascan.Camera.getCameras().then(function (cameras) {
			self.cameras = cameras;
			if (cameras.length > 0) {
				self.activeCameraId = cameras[0].id;
				self.scanner.start(cameras[0]);
			} else {
				console.error('No cameras found.');
			}
		}).catch(function (e) {
			console.error(e);
		});
		// evaluate stored and new services
		if (localStorage){ // the browser supports localstorage
			var servicesString =  localStorage.getItem('services');
			self.activeServiceId=localStorage.getItem('activeServiceId')
			self.activeCameraId=localStorage.getItem('activeCameraId')
			if (servicesString){
				self.services=JSON.parse(servicesString)
			}else{
				self.services=[]
			}
			const queryString = window.location.search;
			console.log(queryString);
			const urlParams = new URLSearchParams(queryString);
			if(urlParams.has('servicename') && urlParams.has('servicebot')){
				const newServiceName = urlParams.get('servicename')
				const newServiceBot = urlParams.get('servicebot')
				console.log(newServiceName,newServiceBot)
				var arrayLength = self.services.length;
				var foundFlag = false
				for (var i = 0; i < arrayLength; i++) {
					var service=self.services[i]
					console.log(service);
					if (service.name==newServiceName){
						foundFlag=true
						service.bot=newServiceBot
						break
					}
				}
				if (!foundFlag){
					self.services.push({"name":newServiceName,'bot':newServiceBot,'id':arrayLength})
				}
				localStorage.setItem('services',JSON.stringify(self.services) )
			}
		}else{
			console.log("no local storage!?!")
		}
	},
	methods: {
		formatName: function (name) {
			return name || '(unknown)';
		},
		selectCamera: function (camera) {
			this.activeCameraId = camera.id;
			if (localStorage){ // the browser supports localstorage
				localStorage.setItem('activeCameraId',camera.id)
			}
			this.scanner.start(camera);
		},
		selectService: function (service) {
			this.activeServiceId = service.id;
			if (localStorage){ // the browser supports localstorage
				localStorage.setItem('activeServiceId',service.id)
			}
		}
	}
});
