// Get all reachable countries map from https://travle.earth/practice?r=g_PAN_GTM
// Click on Configure, then Route
// Then copy and paste this script in the Console

// copy all country names
function getCountries(options) {
	let countries = {};
	for (let op of options) {
		if (op.value != "random") countries[op.value] = op.textContent;
	}
	return countries;
}

function getSources() {
	return document
		.getElementsByTagName("article")[0]
		?.getElementsByTagName("div")[0]
		?.getElementsByTagName("div")[0]
		?.getElementsByTagName("select");
}
let sources = getSources();
let countries = getCountries(sources[0].getElementsByTagName("option"));

let selectionChanged = new Event("change", { bubbles: true });

function updateMap(obj, countries) {
	let _sources = getSources();
	let reachables = [];
	if (_sources && _sources[1]) {
		let target = _sources[1].getElementsByTagName("option");
		for (let op of target) {
			if (op.value != "random") reachables.push(op.textContent);
		}
	}
	if (_sources[0].value != "random") {
		let id = countries[_sources[0].value];
		console.log(id, "-------------------ID");
		console.log("reachable list: ", reachables.lengh);
		obj[id] = reachables;
	}
}

async function waitForChange() {
	return new Promise((resolve) =>
		setTimeout(() => {
			resolve();
		}, 1000)
	);
}

async function getReachableCountries(country, _sources, changeEvent) {
	_sources[0].value = country;
	_sources[0].dispatchEvent(changeEvent);
}

let reachable = {};

for (let c of Object.keys(countries)) {
	getReachableCountries(c, sources, selectionChanged);
	await waitForChange();
	updateMap(reachable, countries);
}

reachable;
