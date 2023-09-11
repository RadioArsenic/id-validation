import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:camera/camera.dart';
import 'dart:io';

import 'camera_screen.dart';

//late - variables are value is assigned l
late List<CameraDescription> cameras;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  cameras = await availableCameras();
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({Key? key}) : super(key: key);

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(primarySwatch: Colors.blue),
      home: HomeScreen(),
    );
  }
}

String stringResponse = "";
// currently a url to api for random user generator
const apiURL = "http://10.0.2.2:5000/api?query=2";

class HomeScreen extends StatefulWidget {
  const HomeScreen({Key? key}) : super(key: key);

  @override
  _HomeScreenState createState() => _HomeScreenState();
}

// code for the homescreen of the app
class _HomeScreenState extends State<HomeScreen> {
  // camera variable
  late CameraController _controller;

  Future apicall() async {
    http.Response response;
    response = await http.get(Uri.parse(apiURL));
    if (response.statusCode == 200) {
      setState(() {
        stringResponse = response.body;
      });
    }
  }

  @override
  void initState() {
    apicall();
    super.initState();
    _controller = CameraController(cameras[0], ResolutionPreset.max);
    
    // initialize the first available camera
    _controller.initialize().then((_) {
      if (!mounted) {
        return;
      }
      setState(() {});
    }).catchError((Object e) {
      if (e is CameraException) {
        switch (e.code) {
          case 'CameraAccessDenited':
            print("acces was denied");
            break;
          default:
            print(e.description);
            break;
        }
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      //text and bars of the app (decorations)
      appBar: AppBar(title: Text("OCR program")),
      body: Stack(
        children: [
          SizedBox(
            height: double.infinity,
            child: CameraPreview(_controller),
          ),
          Center(
            child: Container(
                height: 200,
                width: 300,
                decoration: BoxDecoration(
                  // the white box for the card outline
                  border: Border.all(color: Colors.white),
                ),
                child: Center(
                    child: Text(stringResponse.toString()),
                )),
          ),
          Column(
            mainAxisAlignment: MainAxisAlignment.end,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Center(
                child: Container(
                  // adding a margin
                  margin: const EdgeInsets.all(20.0),
                  child: MaterialButton(
                    onPressed: () async {
                      if (!_controller.value.isInitialized) {
                        return;
                      }
                      if (_controller.value.isTakingPicture) {
                        return;
                      }

                      try {
                        await _controller.setFlashMode(FlashMode.auto);
                        XFile file = await _controller.takePicture();
  
                        // Uploading the image to the api
                        await uploadImage(File(file.path));

                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => ImagePreview(file),
                          ),
                        );
                      } on CameraException catch (e) {
                        debugPrint("Error occurred while taking picture: $e");
                        return null;
                      }
                    },
                    color: Colors.white,
                    child: const Text("Take a picture"),
                  ),
                ),
              )
            ],
          )
        ],
      ),
    );
  }
}

Future<void> uploadImage(File imageFile) async {
  // The URL for the image upload, here this was the local flask app used
  var uri = Uri.parse("http://10.0.2.2:5000/upload");

  //usage of mulipart to transfer the image data
  var request = http.MultipartRequest('POST', uri)
    ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

  var response = await request.send();
  
  if (response.statusCode == 200) {
    print('Image uploaded!');
  } else {
    print('Image upload failed.');
  }
}
